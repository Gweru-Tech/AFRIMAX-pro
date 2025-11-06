import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import anthropic
import stripe
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ladybug-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ladybug.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Handle postgres:// to postgresql://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

db = SQLAlchemy(app)
CORS(app)

# API Keys
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    premium_until = db.Column(db.DateTime, nullable=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Usage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    count = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref=db.backref('usage', lazy=True))

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('conversations', lazy=True))

# Create tables
with app.app_context():
    db.create_all()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Rate limiting function
def check_rate_limit(user_id):
    user = User.query.get(user_id)
    if not user:
        return False, "User not found"
    
    # Check if premium and valid
    if user.is_premium and user.premium_until and user.premium_until > datetime.utcnow():
        daily_limit = 10
    else:
        daily_limit = 5
    
    # Get today's usage
    today = datetime.utcnow().date()
    usage = Usage.query.filter_by(user_id=user_id, date=today).first()
    
    if not usage:
        usage = Usage(user_id=user_id, date=today, count=0)
        db.session.add(usage)
        db.session.commit()
    
    if usage.count >= daily_limit:
        return False, f"Daily limit reached. {'Premium' if user.is_premium else 'Free'} users get {daily_limit} requests per day."
    
    return True, daily_limit - usage.count

def increment_usage(user_id):
    today = datetime.utcnow().date()
    usage = Usage.query.filter_by(user_id=user_id, date=today).first()
    if usage:
        usage.count += 1
    else:
        usage = Usage(user_id=user_id, date=today, count=1)
        db.session.add(usage)
    db.session.commit()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    return jsonify({
        'message': 'Registration successful',
        'user': {'email': user.email, 'is_premium': user.is_premium}
    })

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user.id
    return jsonify({
        'message': 'Login successful',
        'user': {
            'email': user.email,
            'is_premium': user.is_premium,
            'premium_until': user.premium_until.isoformat() if user.premium_until else None
        }
    })

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/status')
@login_required
def status():
    user = User.query.get(session['user_id'])
    today = datetime.utcnow().date()
    usage = Usage.query.filter_by(user_id=user.id, date=today).first()
    
    can_use, remaining = check_rate_limit(user.id)
    
    return jsonify({
        'user': {
            'email': user.email,
            'is_premium': user.is_premium,
            'premium_until': user.premium_until.isoformat() if user.premium_until else None
        },
        'usage': {
            'today': usage.count if usage else 0,
            'remaining': remaining if isinstance(remaining, int) else 0,
            'limit': 10 if user.is_premium else 5
        }
    })

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    user_id = session['user_id']
    
    # Check rate limit
    can_use, message = check_rate_limit(user_id)
    if not can_use:
        return jsonify({'error': message}), 429
    
    data = request.get_json()
    user_message = data.get('message')
    mode = data.get('mode', 'general')  # general, code, research, video, logo
    conversation_id = data.get('conversation_id')
    
    if not user_message:
        return jsonify({'error': 'Message required'}), 400
    
    # Load or create conversation
    if conversation_id:
        conv = Conversation.query.get(conversation_id)
        if not conv or conv.user_id != user_id:
            return jsonify({'error': 'Conversation not found'}), 404
        messages = json.loads(conv.messages)
    else:
        messages = []
        conv = None
    
    # Add system message based on mode
    system_prompts = {
        'general': "You are Ladybug AI, a helpful and friendly AI assistant created to help users with various tasks. Be concise, accurate, and helpful.",
        'code': "You are Ladybug AI, an expert programming assistant. Help users with coding tasks, debugging, and software development. Provide clean, well-commented code with explanations.",
        'research': "You are Ladybug AI, a research assistant. Help users find information, analyze data, and provide comprehensive, well-sourced insights on topics.",
        'video': "You are Ladybug AI, a video editing assistant. Help users with video editing concepts, scripts, storyboards, and video production advice.",
        'logo': "You are Ladybug AI, a logo design assistant. Help users brainstorm logo ideas, understand design principles, and create effective brand identities."
    }
    
    system_message = system_prompts.get(mode, system_prompts['general'])
    
    # Add user message
    messages.append({
        'role': 'user',
        'content': user_message
    })
    
    try:
        # Call Anthropic API
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            system=system_message,
            messages=messages
        )
        
        assistant_message = response.content[0].text
        
        # Add assistant message
        messages.append({
            'role': 'assistant',
            'content': assistant_message
        })
        
        # Save conversation
        if conv:
            conv.messages = json.dumps(messages)
        else:
            conv = Conversation(
                user_id=user_id,
                messages=json.dumps(messages)
            )
            db.session.add(conv)
        
        db.session.commit()
        
        # Increment usage
        increment_usage(user_id)
        
        return jsonify({
            'response': assistant_message,
            'conversation_id': conv.id,
            'mode': mode
        })
        
    except Exception as e:
        return jsonify({'error': f'AI service error: {str(e)}'}), 500

@app.route('/conversations')
@login_required
def get_conversations():
    user_id = session['user_id']
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).all()
    
    return jsonify({
        'conversations': [{
            'id': conv.id,
            'created_at': conv.created_at.isoformat(),
            'preview': json.loads(conv.messages)[0]['content'][:100] if conv.messages else ''
        } for conv in conversations]
    })

@app.route('/conversation/<int:conv_id>')
@login_required
def get_conversation(conv_id):
    user_id = session['user_id']
    conv = Conversation.query.get(conv_id)
    
    if not conv or conv.user_id != user_id:
        return jsonify({'error': 'Conversation not found'}), 404
    
    return jsonify({
        'id': conv.id,
        'messages': json.loads(conv.messages),
        'created_at': conv.created_at.isoformat()
    })

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    try:
        # Create Stripe customer if doesn't exist
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email)
            user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': 500,  # $5.00
                    'product_data': {
                        'name': 'Ladybug AI Premium - 30 Days',
                        'description': '10 AI requests per day for 30 days',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.host_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'cancel',
            metadata={
                'user_id': user_id
            }
        )
        
        return jsonify({'checkout_url': checkout_session.url})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle successful payment
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        user_id = int(session_data['metadata']['user_id'])
        
        user = User.query.get(user_id)
        if user:
            user.is_premium = True
            user.premium_until = datetime.utcnow() + timedelta(days=30)
            db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

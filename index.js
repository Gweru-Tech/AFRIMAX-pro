require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const bodyParser = require('body-parser');
const { RateLimiterMemory } = require('rate-limiter-flexible');
const aiService = require('./services/aiService');
const codeGenerator = require('./services/codeGenerator');
const logoGenerator = require('./services/logoGenerator');
const imageAnalyzer = require('./services/imageAnalyzer');

const app = express();
const PORT = process.env.PORT || 3000;

// Rate limiter configuration
const rateLimiter = new RateLimiterMemory({
  points: 10, // 10 requests
  duration: 60, // per 60 seconds
});

// Middleware
app.use(helmet());
app.use(cors());
app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '10mb' }));

// Rate limiting middleware
const rateLimiterMiddleware = async (req, res, next) => {
  try {
    await rateLimiter.consume(req.ip);
    next();
  } catch (rejRes) {
    res.status(429).json({
      success: false,
      message: 'Too many requests. Please try again later.',
    });
  }
};

// Health check endpoint
app.get('/', (req, res) => {
  res.json({
    success: true,
    message: 'Ladybug AI is running!',
    version: '2.0.0',
    endpoints: {
      chat: 'POST /api/chat',
      code: 'POST /api/code',
      logo: 'POST /api/logo',
      analyze: 'POST /api/analyze',
    },
  });
});

// Main chat endpoint
app.post('/api/chat', rateLimiterMiddleware, async (req, res) => {
  try {
    const { content, user, imageBuffer } = req.body;

    if (!content) {
      return res.status(400).json({
        success: false,
        message: 'Content is required',
      });
    }

    let response;
    
    if (imageBuffer) {
      response = await imageAnalyzer.analyzeImage(imageBuffer, content);
    } else {
      response = await aiService.chat(content, user);
    }

    res.json({
      success: true,
      result: response,
    });
  } catch (error) {
    console.error('Chat error:', error);
    res.status(500).json({
      success: false,
      message: 'An error occurred processing your request',
      error: error.message,
    });
  }
});

// Code generation endpoint
app.post('/api/code', rateLimiterMiddleware, async (req, res) => {
  try {
    const { prompt, language } = req.body;

    if (!prompt) {
      return res.status(400).json({
        success: false,
        message: 'Prompt is required',
      });
    }

    const code = await codeGenerator.generate(prompt, language);

    res.json({
      success: true,
      result: code,
    });
  } catch (error) {
    console.error('Code generation error:', error);
    res.status(500).json({
      success: false,
      message: 'An error occurred generating code',
      error: error.message,
    });
  }
});

// Logo generation endpoint
app.post('/api/logo', rateLimiterMiddleware, async (req, res) => {
  try {
    const { text, style, colors } = req.body;

    if (!text) {
      return res.status(400).json({
        success: false,
        message: 'Text is required for logo generation',
      });
    }

    const logo = await logoGenerator.generate(text, style, colors);

    res.json({
      success: true,
      result: logo,
      message: 'Logo generated successfully',
    });
  } catch (error) {
    console.error('Logo generation error:', error);
    res.status(500).json({
      success: false,
      message: 'An error occurred generating logo',
      error: error.message,
    });
  }
});

// Image analysis endpoint
app.post('/api/analyze', rateLimiterMiddleware, async (req, res) => {
  try {
    const { imageBuffer, question } = req.body;

    if (!imageBuffer) {
      return res.status(400).json({
        success: false,
        message: 'Image is required',
      });
    }

    const analysis = await imageAnalyzer.analyzeImage(imageBuffer, question);

    res.json({
      success: true,
      result: analysis,
    });
  } catch (error) {
    console.error('Image analysis error:', error);
    res.status(500).json({
      success: false,
      message: 'An error occurred analyzing image',
      error: error.message,
    });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    message: 'Something went wrong!',
  });
});

app.listen(PORT, () => {
  console.log(`🐞 Ladybug AI server running on port ${PORT}`);
});

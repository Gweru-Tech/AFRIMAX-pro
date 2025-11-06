const axios = require('axios');

class AIService {
  constructor() {
    this.systemPrompt = `You are Ladybug, an advanced AI assistant created to help everyone with their questions and tasks. 
    
Your capabilities include:
- Writing and debugging code in any programming language
- Creating logos and designs
- Analyzing images and providing detailed descriptions
- Solving complex problems
- Providing educational content
- Offering creative solutions

You are helpful, knowledgeable, and friendly. You provide clear, accurate, and useful responses to help users accomplish their goals. You always follow ethical guidelines and promote positive, constructive interactions.`;
  }

  async chat(content, user = 'anonymous') {
    try {
      // Using a free AI API (you can replace with OpenAI, Anthropic, etc.)
      const response = await axios.post('https://luminai.my.id', {
        content: content,
        user: user,
        prompt: this.systemPrompt,
      });

      return response.data.result;
    } catch (error) {
      // Fallback to another API or local processing
      console.error('Primary AI service error:', error.message);
      return await this.fallbackResponse(content);
    }
  }

  async fallbackResponse(content) {
    // Simple fallback for when primary service is down
    const lowerContent = content.toLowerCase();
    
    if (lowerContent.includes('code') || lowerContent.includes('programming')) {
      return "I can help you with coding! Please specify what programming language you'd like to use and what you'd like to build.";
    }
    
    if (lowerContent.includes('logo') || lowerContent.includes('design')) {
      return "I can help create logos! Use the /api/logo endpoint with your desired text and style preferences.";
    }
    
    return "Hello! I'm Ladybug AI. I can help with coding, logo creation, image analysis, and much more. How can I assist you today?";
  }
}

module.exports = new AIService();

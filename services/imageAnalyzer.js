const axios = require('axios');

class ImageAnalyzer {
  async analyzeImage(imageBuffer, question = 'Describe this image') {
    try {
      // Convert buffer to base64 if needed
      const base64Image = Buffer.isBuffer(imageBuffer) 
        ? imageBuffer.toString('base64')
        : imageBuffer;

      const response = await axios.post('https://luminai.my.id', {
        content: question,
        imageBuffer: base64Image,
        prompt: 'You are an expert at analyzing images. Provide detailed, accurate descriptions and answer questions about images.',
      });

      return response.data.result;
    } catch (error) {
      console.error('Image analysis error:', error);
      return 'I can see an image, but I need additional context to analyze it properly. Could you describe what you\'d like to know about it?';
    }
  }
}

module.exports = new ImageAnalyzer();

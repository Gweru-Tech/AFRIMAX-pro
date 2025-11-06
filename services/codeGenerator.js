const axios = require('axios');

class CodeGenerator {
  async generate(prompt, language = 'javascript') {
    try {
      const enhancedPrompt = `Generate ${language} code for the following request. Provide clean, well-commented, production-ready code:\n\n${prompt}`;
      
      const response = await axios.post('https://luminai.my.id', {
        content: enhancedPrompt,
        prompt: 'You are an expert programmer. Generate clean, efficient, well-documented code. Include comments explaining the logic.',
      });

      return this.formatCode(response.data.result, language);
    } catch (error) {
      return this.generateBasicCode(prompt, language);
    }
  }

  formatCode(code, language) {
    return {
      language: language,
      code: code,
      timestamp: new Date().toISOString(),
    };
  }

  generateBasicCode(prompt, language) {
    const templates = {
      javascript: `// ${prompt}\n\nfunction solution() {\n  // Your code here\n  console.log("Implementation needed");\n}\n\nsolution();`,
      python: `# ${prompt}\n\ndef solution():\n    # Your code here\n    print("Implementation needed")\n\nsolution()`,
      java: `// ${prompt}\n\npublic class Solution {\n    public static void main(String[] args) {\n        // Your code here\n        System.out.println("Implementation needed");\n    }\n}`,
    };

    return {
      language: language,
      code: templates[language] || templates.javascript,
      timestamp: new Date().toISOString(),
    };
  }
}

module.exports = new CodeGenerator();

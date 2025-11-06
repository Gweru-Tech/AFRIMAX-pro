const { createCanvas } = require('canvas');

class LogoGenerator {
  async generate(text, style = 'modern', colors = ['#FF6B6B', '#4ECDC4']) {
    try {
      const canvas = createCanvas(800, 800);
      const ctx = canvas.getContext('2d');

      // Background
      const gradient = ctx.createLinearGradient(0, 0, 800, 800);
      gradient.addColorStop(0, colors[0] || '#FF6B6B');
      gradient.addColorStop(1, colors[1] || '#4ECDC4');
      
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 800, 800);

      // Add style-specific elements
      if (style === 'modern') {
        this.drawModernStyle(ctx, text);
      } else if (style === 'minimal') {
        this.drawMinimalStyle(ctx, text);
      } else if (style === 'tech') {
        this.drawTechStyle(ctx, text);
      } else {
        this.drawDefaultStyle(ctx, text);
      }

      // Convert to base64
      const buffer = canvas.toBuffer('image/png');
      const base64 = buffer.toString('base64');

      return {
        image: `data:image/png;base64,${base64}`,
        width: 800,
        height: 800,
        style: style,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      console.error('Logo generation error:', error);
      throw new Error('Failed to generate logo');
    }
  }

  drawModernStyle(ctx, text) {
    // Circle background
    ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.beginPath();
    ctx.arc(400, 400, 300, 0, Math.PI * 2);
    ctx.fill();

    // Text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 80px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 400, 400);
  }

  drawMinimalStyle(ctx, text) {
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 100px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 400, 400);
  }

  drawTechStyle(ctx, text) {
    // Hexagon shape
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.lineWidth = 5;
    this.drawHexagon(ctx, 400, 400, 250);

    // Text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 70px Courier New';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 400, 400);
  }

  drawDefaultStyle(ctx, text) {
    // Simple centered text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 90px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
    ctx.shadowBlur = 10;
    ctx.fillText(text, 400, 400);
  }

  drawHexagon(ctx, x, y, size) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i;
      const xPos = x + size * Math.cos(angle);
      const yPos = y + size * Math.sin(angle);
      if (i === 0) {
        ctx.moveTo(xPos, yPos);
      } else {
        ctx.lineTo(xPos, yPos);
      }
    }
    ctx.closePath();
    ctx.stroke();
  }
}

module.exports = new LogoGenerator();

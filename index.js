//Imports
const express = require('express');
const { spawn, execSync, exec } = require('child_process');
const fs = require('fs');
const path = require('path');
require('dotenv/config');
const axios = require('axios');
const FormData = require('form-data');
const { platform } = require('os');
const { stderr } = require('process');
const app = express();

app.use(express.json({ limit: '50mb' }));

//Groq Transcription Endpoint
app.post('/api/transcribe-groq', async (req, res) => {
  const tempFile = path.join(__dirname, 'temp_groq_audio.wav');
  
  try {
    const { audio } = req.body;
    
    if (!audio) {
      return res.status(400).json({ error: 'Missing audio parameter' });
    }
    
    console.log('Transcribing with Groq Whisper...');
    
    // Convert base64 to buffer
    const audioBuffer = Buffer.from(audio, 'base64');
    console.log('Audio buffer size:', audioBuffer.length, 'bytes');
    
    // Validate WAV
    if (audioBuffer.length < 12 || audioBuffer.toString('ascii', 0, 4) !== 'RIFF') {
      return res.status(400).json({ error: 'Invalid WAV file' });
    }
    
    // Save to temp file
    fs.writeFileSync(tempFile, audioBuffer);
    
    // Create FormData
    const form = new FormData();
    form.append('file', fs.createReadStream(tempFile), 'audio.wav');
    form.append('model', 'whisper-large-v3');
    form.append('language', 'en');
    
    // Send with axios
    const response = await axios.post(
      'https://api.groq.com/openai/v1/audio/transcriptions',
      form,
      {
        headers: {
          'Authorization': `Bearer ${process.env.GROQ_API_KEY}`,
          ...form.getHeaders()
        }
      }
    );
    
    // Clean up
    try {
      fs.unlinkSync(tempFile);
    } catch (e) {}
    
    const transcription = response.data.text.trim();
    console.log('Transcription:', transcription);
    
    const hasGreek = /[\u0370-\u03FF]/.test(transcription);
    
    res.json({ 
      transcription: transcription,
      language: hasGreek ? 'el' : 'en',
      success: true 
    });
    
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    
    try {
      if (fs.existsSync(tempFile)) fs.unlinkSync(tempFile);
    } catch (e) {}
    
    res.status(500).json({ 
      error: error.response?.data?.error?.message || error.message 
    });
  }
});
//Ask Endpoint
app.post('/api/ask', async (req, res) => {
  try {
    console.log('Received request with keys:', Object.keys(req.body));
    const { text, context, image, conversationHistory } = req.body;

    const now = new Date();
    const timeString = now.toLocaleTimeString('el-GR', {
      timeZone: 'Europe/Athens',
      hour: '2-digit',
      minute: '2-digit'
    });

    // Validate input
    if (!text) {
      return res.status(400).json({ error: 'Missing text parameter' });
    }

    // Build system prompt with context
    let systemPrompt = "You are ATLAS, a helpful AI assistant that speaks Greek. Be brief and concise.";

    if (context) {
      systemPrompt += ` Current time: ${timeString}.`;
      if (context.temperature) systemPrompt += ` Temp: ${context.temperature}°C.`;
      if (context.humidity) systemPrompt += ` Humidity: ${context.humidity}%.`;
      if (context.location) systemPrompt += ` Location: ${context.location}.`;
    }

    console.log('Making request to Groq...');

    // Build messages array starting with system prompt
    const messages = [
      { role: 'system', content: systemPrompt }
    ];

    // Add conversation history if provided
    if (conversationHistory && Array.isArray(conversationHistory)) {
      console.log(`Adding ${conversationHistory.length} messages from history`);
      messages.push(...conversationHistory);
    }

    // Add current user message
    // Note: Groq doesn't support vision/images yet, so we ignore image parameter
    if (image) {
      console.log('Warning: Image provided but Groq does not support vision. Ignoring image.');
    }

    messages.push({
      role: 'user',
      content: text
    });

    // Use Groq API (FREE!)
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.GROQ_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'llama-3.3-70b-versatile', // Free, fast, good quality
        messages: messages,
        max_tokens: 300,
        temperature: 0.7
      }),
    });

    console.log('Response status:', response.status);

    const data = await response.json();

    if (process.env.DEBUG) {
      console.log('Full API response:', JSON.stringify(data, null, 2));
    }

    // Check for error in response
    if (data.error) {
      return res.status(400).json({
        error: 'Groq error',
        details: data.error
      });
    }

    // Safely access choices
    const answer = data.choices?.[0]?.message?.content;

    if (!answer) {
      return res.status(500).json({
        error: 'No response from AI',
        fullResponse: data
      });
    }

    // Return response with updated conversation history
    res.json({
      response: answer,
      conversationHistory: [
        ...(conversationHistory || []),
        { role: 'user', content: text },
        { role: 'assistant', content: answer }
      ]
    });

  } catch (error) {
    console.error('Caught error:', error);
    res.status(500).json({ error: error.message, stack: error.stack });
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// System commands endpoint
app.post('/api/system-commands', async (req, res) => {
  try {
    const { action, parameter } = req.body;

    console.log(`💻 System command: ${action} ${parameter || ''}`);

    let command;

    switch (action) {
      case 'open-url':
        //  Open URL in browser
        const url = parameter;
        if (process.platform === 'win32') {
          command = `open "${url}"`;
        }
        break;

        case 'open-app':
          // Open Applications
          const app = parameter;
          if (process.platform === 'win32') {
            command = `start "" "${app}"`;
          }
        break;

        case 'search-google':
          // Google Search
          const query = encodeURIComponent(parameter);
          const search_url = `https://google.com/search?q=${query}`
          if (process.platform === 'win32') {
            command = `start "" "${search_url}"`
          }
          break;

          default:
            return res.status(400).json({ error: 'Unknown action'});
    }
    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error('❌ Command error:', error);
        return res.status(500).json({ error: error.message });
      }
      console.log(`✅ Executed: ${action}`);
      res.json({
        success: true,
        message: `Executed: ${action}`
      });
    });
  } catch (error) {
    console.error('System command error:', error);
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, () => console.log(`ATLAS API running on port ${PORT} (using Groq - FREE)`));
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} in use. Set PORT env or free the port.`);
    process.exit(1);
  }
  console.error('Server error:', err);
});
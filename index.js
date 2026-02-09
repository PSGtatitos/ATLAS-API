const express = require('express');
const { spawn, execSync } = require('child_process');  // ← Make sure this is here
const fs = require('fs');                    // ← Make sure this is here
const path = require('path');                // ← Make sure this is here
require('dotenv/config');

const app = express();
app.use(express.json({ limit: '50mb' }));

app.post('/api/transcribe', async (req, res) => {
  try {
    const { audio } = req.body;
    
    if (!audio) {
      return res.status(400).json({ error: 'Missing audio parameter' });
    }
    
    console.log('Transcribing with Vosk (Greek)...');
    console.log('Audio data length:', audio.length);
    
    // Convert base64 to buffer
    const audioBuffer = Buffer.from(audio, 'base64');
    console.log('Audio buffer size:', audioBuffer.length, 'bytes');
    
    // Validate RIFF WAV header
    if (audioBuffer.length < 12 || audioBuffer.toString('ascii', 0, 4) !== 'RIFF' || audioBuffer.toString('ascii', 8, 12) !== 'WAVE') {
      console.error('Audio is not a valid WAV file (missing RIFF header)');
      return res.status(400).json({ error: 'Audio must be a valid WAV file (RIFF format)' });
    }
    
    // Create temp file path
    const tempFile = path.join(__dirname, 'temp_audio.wav');
    console.log('Temp file path:', tempFile);
    
    // Write the file
    fs.writeFileSync(tempFile, audioBuffer);
    console.log('Temp file written successfully');
    
    // Verify file exists
    if (!fs.existsSync(tempFile)) {
      return res.status(500).json({ error: 'Failed to create temp audio file' });
    }
    
    const pythonScript = path.join(__dirname, 'vosk_transcribe.py');

    // Support multiple Vosk models via env vars:
    // VOSK_MODEL_PATH (legacy), or VOSK_MODEL_PATH_EN and VOSK_MODEL_PATH_EL
    const modelEnvDefault = process.env.VOSK_MODEL_PATH;
    const modelEn = process.env.VOSK_MODEL_PATH_EN;
    const modelEl = process.env.VOSK_MODEL_PATH_EL;

    // Allow clients to request language via `language` or `lang` in the body
    const reqLang = (req.body.language || req.body.lang || '').toString().toLowerCase();
    let modelPath;
    if (reqLang === 'el' || reqLang === 'greek' || reqLang === 'gr') {
      modelPath = modelEl || modelEnvDefault || modelEn;
    } else if (reqLang === 'en' || reqLang === 'english') {
      modelPath = modelEn || modelEnvDefault || modelEl;
    } else {
      // No explicit language requested: prefer default env, then English, then Greek
      modelPath = modelEnvDefault || modelEn || modelEl;
    }

    console.log('Python script:', pythonScript);
    console.log('Requested language:', reqLang || '(auto)');

    if (!modelPath && !modelEn && !modelEl) {
      try { fs.unlinkSync(tempFile); } catch (e) {}
      return res.status(500).json({ error: 'No Vosk model configured. Set VOSK_MODEL_PATH or VOSK_MODEL_PATH_EN/VOSK_MODEL_PATH_EL in .env' });
    }

    // Helper to run the python transcription and collect stdout/stderr
    const runPython = (mpath) => new Promise((resolve) => {
      const proc = spawn('python', [pythonScript, tempFile, mpath]);
      let out = '';
      let err = '';
      proc.stdout.on('data', (d) => { out += d.toString(); console.log('python stdout chunk'); });
      proc.stderr.on('data', (d) => { err += d.toString(); console.log('python stderr chunk'); });
      proc.on('close', (code) => resolve({ code, out: out.trim(), err }));
      proc.on('error', (e) => resolve({ code: 1, out: '', err: String(e) }));
    });

    // Auto-detect strategy when language not explicitly requested and both models exist
    let finalTranscription = '';
    let finalLang = reqLang || '';

    const tryModels = async () => {
      // Build candidate list depending on availability and preference
      const candidates = [];
      if (modelPath) candidates.push({ path: modelPath, tag: reqLang || 'default' });
      // If no explicit modelPath or we want to try both, add en/el if available
      if (modelEn && (!candidates.find(c => c.path === modelEn))) candidates.push({ path: modelEn, tag: 'en' });
      if (modelEl && (!candidates.find(c => c.path === modelEl))) candidates.push({ path: modelEl, tag: 'el' });

      for (const candidate of candidates) {
        console.log('Trying model:', candidate.path, 'tag:', candidate.tag);
        const result = await runPython(candidate.path);
        console.log('python result code', result.code, 'out len', result.out.length);
        if (result.code === 0 && result.out && result.out.length > 0) {
          // If contains Greek characters, mark as Greek
          const hasGreek = /[\u0370-\u03FF]/.test(result.out);
          finalTranscription = result.out;
          finalLang = hasGreek ? 'el' : 'en';
          return { ok: true };
        }
        // else continue to next candidate
      }
      return { ok: false };
    };

    const tried = await tryModels();

    // Clean up temp file
    try { if (fs.existsSync(tempFile)) fs.unlinkSync(tempFile); } catch (e) { console.error('Cleanup failed', e); }

    if (!tried.ok) {
      return res.status(500).json({ error: 'Vosk transcription failed', details: 'No model produced output' });
    }

    console.log('Transcription result:', finalTranscription, 'lang:', finalLang);
    return res.json({ transcription: finalTranscription, language: finalLang, success: true });
    
  } catch (error) {
    console.error('Transcription error:', error);
    res.status(500).json({ error: error.message, stack: error.stack });
  }
});

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
    }
    
    console.log('Making request to OpenRouter...');
    
    // Build messages array starting with system prompt
    const messages = [
      { role: 'system', content: systemPrompt }
    ];
    
    // Add conversation history if provided
    if (conversationHistory && Array.isArray(conversationHistory)) {
      console.log(`Adding ${conversationHistory.length} messages from history`);
      messages.push(...conversationHistory);
    }
    
    // Add current user message with or without image
    if (image) {
      console.log('Image detected, using vision capabilities');
      messages.push({
        role: 'user',
        content: [
          { type: 'text', text: text },
          { 
            type: 'image_url', 
            image_url: { 
              url: image.startsWith('data:') ? image : `data:image/jpeg;base64,${image}`
            } 
          }
        ]
      });
    } else {
      messages.push({ 
        role: 'user', 
        content: text 
      });
    }
    
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:3000',
        'X-Title': 'ATLAS Assistant'
      },
      body: JSON.stringify({
        model: 'anthropic/claude-sonnet-4',
        messages: messages,
        max_tokens: 300
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
        error: 'OpenRouter error', 
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

const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, () => console.log(`ATLAS API running on port ${PORT}`));
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} in use. Set PORT env or free the port.`);
    process.exit(1);
  }
  console.error('Server error:', err);
});
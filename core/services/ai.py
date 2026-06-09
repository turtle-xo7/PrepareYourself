"""Shared AI provider gateway (Anthropic + Gemini).

All outbound AI calls go through here so every view gets the same
timeout, error handling, and logging instead of repeating urllib
boilerplate.
"""
import base64
import json
import logging
import urllib.request
import urllib.error

from django.conf import settings

logger = logging.getLogger('core')

ANTHROPIC_MODEL = 'claude-sonnet-4-20250514'
REQUEST_TIMEOUT = 60  # seconds


class AIServiceError(Exception):
    """AI provider call failed. str(exc) is safe to show to the user."""


def anthropic_complete(prompt, max_tokens=2000):
    """Send a single-message completion to the Anthropic API and return the text."""
    if not settings.ANTHROPIC_API_KEY:
        raise AIServiceError(
            'Anthropic API key is not configured. Set ANTHROPIC_API_KEY in your .env file.'
        )

    payload = json.dumps({
        'model': ANTHROPIC_MODEL,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': prompt}],
    }, ensure_ascii=False).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json; charset=utf-8',
            'anthropic-version': '2023-06-01',
            'x-api-key': settings.ANTHROPIC_API_KEY,
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            result = json.loads(response.read().decode('utf-8'))
        return result['content'][0]['text']
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        logger.error('Anthropic API error: HTTP %s — %.300s', e.code, body)
        raise AIServiceError(f'AI service error (HTTP {e.code}).') from e
    except AIServiceError:
        raise
    except Exception as e:
        logger.exception('Anthropic API call failed')
        raise AIServiceError(f'AI service unavailable: {e}') from e


def gemini_extract_text(image_bytes, mime_type='image/jpeg'):
    """OCR an image with Gemini and return the extracted text."""
    if not settings.GEMINI_API_KEY:
        raise AIServiceError(
            'Gemini API key is not configured. Set GEMINI_API_KEY in your .env file.'
        )

    payload = json.dumps({
        'contents': [{
            'parts': [
                {'inline_data': {
                    'mime_type': mime_type,
                    'data': base64.b64encode(image_bytes).decode('utf-8'),
                }},
                {'text': 'এই ছবিতে থাকা সব বাংলা ও ইংরেজি টেক্সট হুবহু extract করো। '
                         'শুধু টেক্সট দাও, কোনো ব্যাখ্যা বা মন্তব্য যোগ করো না।'},
            ]
        }],
        'generationConfig': {'temperature': 0, 'maxOutputTokens': 4096},
    }).encode('utf-8')

    url = ('https://generativelanguage.googleapis.com/v1beta/models/'
           f'gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}')
    req = urllib.request.Request(url, data=payload,
                                 headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        return result['candidates'][0]['content']['parts'][0]['text']
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        logger.error('Gemini OCR failed: HTTP %s — %.300s', e.code, body)
        raise AIServiceError(f'Gemini error {e.code}: {body[:300]}') from e
    except AIServiceError:
        raise
    except Exception as e:
        logger.exception('Gemini OCR failed')
        raise AIServiceError(str(e)) from e

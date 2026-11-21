# Add these routes to app.py

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        agent = create_gemini_agent()
        system_prompt = 'You are a helpful AI travel assistant for YatraPilot. Help users plan trips.'
        
        response_text = agent.chat_with_tools(
            messages=[{'role': 'user', 'content': message}],
            system_prompt=system_prompt,
            max_iterations=3
        )
        
        return jsonify({'response': response_text, 'status': 'success'}), 200
    except Exception as e:
        logger.error(f'Chat error: {e}')
        return jsonify({'error': str(e)}), 500

import gradio as gr
import speech_recognition as sr
from main import handle_query
import time

recognizer = sr.Recognizer()

def ui_listen(max_attempts=2):
    for attempt in range(max_attempts):
        with sr.Microphone() as source:
            try:
                print(f"Listening (attempt {attempt+1})...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=5)
                text = recognizer.recognize_google(audio)
                print(f"Recognized: {text}")
                return text
            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError as e:
                print(f"API error: {e}")
            except Exception as e:
                print(f"Error: {e}")
        time.sleep(1)
    return None

def handle_voice(chat_history):
    user_text = ui_listen()
    if not user_text:
        return chat_history + [("", "I didn't catch that. Please try typing or speak again.")]
    
    # Process query with is_voice=False for Gradio
    response = handle_query(user_text, is_voice=False)
    return chat_history + [(user_text, response)]

def handle_text(user_text, chat_history):
    if not user_text.strip():
        return chat_history, ""
    
    # Process query with is_voice=False for Gradio
    response = handle_query(user_text, is_voice=False)
    return chat_history + [(user_text, response)], ""

with gr.Blocks(theme=gr.themes.Soft(), title="AI Voice Travel Assistant") as demo:
    gr.Markdown("""
    # 🎙️ AI Voice Travel Assistant
    *Speak or type your travel requests (weather, hotels, flights, attractions)*
    """)
    
    with gr.Row():
        chatbot = gr.Chatbot(
            height=500,
            bubble_full_width=False,
            show_copy_button=True
        )
        
    with gr.Row():
        with gr.Column(scale=1):
            mic = gr.Button("🎤 Speak", variant="primary")
        with gr.Column(scale=4):
            txt = gr.Textbox(
                placeholder="Ask about hotels in Paris or weather in Tokyo...",
                show_label=False,
                container=False
            )
    
    with gr.Row():
        clear_btn = gr.Button("🧹 Clear Chat", variant="secondary")
    
    # Voice interaction
    mic.click(
        handle_voice,
        inputs=[chatbot],
        outputs=[chatbot]
    )
    
    # Text interaction
    txt.submit(
        handle_text,
        inputs=[txt, chatbot],
        outputs=[chatbot, txt]
    )
    
    # Clear chat
    clear_btn.click(
        fn=lambda: [],
        inputs=[],
        outputs=[chatbot]
    )
    
    # Examples
    gr.Examples(
        examples=[
            ["What's the weather in London?"],
            ["Find hotels in Paris"],
            ["Show flights to Tokyo"],
            ["What attractions are in New York?"],
            ["Show my bookings"]
        ],
        inputs=txt,
        label="Try these examples:"
    )

if __name__ == "__main__":
    demo.launch()
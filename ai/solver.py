import json
import google.generativeai as genai
from config.settings import settings
from ai.prompts import SYSTEM_PROMPT, build_user_prompt
import base64

class AISolver:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def solve(self, exercise_type, text_content, image_b64=None, audios_b64=None):
        if exercise_type == "PRESENTATION":
            return {
                "question": "Actividad de presentación / lectura / escucha / pronunciación",
                "answer": "N/A (Actividad completada sin campos de texto)",
                "confidence": 1.0,
                "explanation": "Esta pantalla es de lectura, escucha o práctica de pronunciación. No contiene preguntas ni campos para rellenar."
            }

        if not self.api_key:
            return {"error": "La clave API de Gemini no está configurada."}
            
        # Priorizar modelos activos, rápidos y con soporte multimodal de audio/imagen
        models_to_try = [
            "models/gemini-3.5-flash-lite",
            "models/gemini-3.1-flash-lite",
            "models/gemini-flash-latest",
            "models/gemini-pro-latest"
        ]
        
        full_prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(exercise_type, text_content)
        contents = [full_prompt]
        
        if image_b64:
            image_data = {
                "mime_type": "image/jpeg",
                "data": base64.b64decode(image_b64)
            }
            contents.append(image_data)
            
        if audios_b64:
            for audio in audios_b64:
                contents.append({
                    "mime_type": audio["mime_type"],
                    "data": base64.b64decode(audio["data"])
                })

        last_error = ""
        for model_name in models_to_try:
            try:
                print(f"[AISolver] Attempting with model: {model_name}...")
                model = genai.GenerativeModel(model_name=model_name)
                response = model.generate_content(
                    contents,
                    generation_config=genai.GenerationConfig(
                        temperature=0.0,
                    )
                )
                
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith("```"):
                    response_text = response_text[3:-3].strip()
                    
                parsed = json.loads(response_text)
                parsed["_model_used"] = model_name
                return parsed
                
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                print(f"[AISolver] Error with {model_name}: {err_str[:80]}")
                if "429" in err_str or "404" in err_str:
                    # Cuota agotada o modelo no disponible, probar el siguiente de inmediato
                    continue
                else:
                    # Otro tipo de error, intentar con el siguiente también
                    continue
                    
        return {"error": f"Todos los modelos agotaron su cuota. Último error: {last_error}", "confidence": 0}

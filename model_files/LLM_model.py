import pandas as pd
import google.generativeai as genai
import os
# ----------------------------------------------  static stuff  --------------------------------------------------

faq_path = "C:/Users/Asus/OneDrive/Desktop/Flask_learn/model_files/faq.xlsx"
gemini_key = "AIzaSyB4eh0IQp63gkGOijYhhCeptQG0vXReLM0"
genai.configure(api_key=gemini_key)

system_prompt = """
For follow-up questions in the same conversation, respond naturally without repeating the full introduction.
Maintain a smooth conversation flow by referencing previous messages when relevant.
Be contextually aware — if someone asks a follow-up question, acknowledge their previous message.
Provide clear and helpful answers based on the available context.
Use "Jai Siyaram!" as a greeting only when appropriate (first interaction or after long gaps).
Be conversational and natural, not robotic or repetitive.
Reference uploaded documents when relevant.
Keep responses concise yet comprehensive.
For specific and factual questions, provide complete, accurate, and detailed answers. Do not omit any information.
For open-ended or abstract questions, offer a concise and thoughtful summary, then ask a follow-up question to clarify the user’s intent or interest.
If multiple answers are relevant, combine or list them clearly.
Prioritize the meaning and context of the question over keywords to provide the most relevant response.
Use only the provided data; do not assume answers. If a question falls outside the available information, respond with:
"I don't have that information."
If there’s any related information available, provide it — otherwise, don’t add anything further.
"""

model_name = "gemini-1.5-flash" 
gemini_model = genai.GenerativeModel(model_name)

# ----------------------------------------------  static stuff  --------------------------------------------------


# ---------------------------------------------  Functions -------------------------------------------------------

# Getting system prompt where ever needed
def get_system_prompt():
    return system_prompt


# Updating the system prompt
def set_system_prompt(new_prompt):
    global system_prompt
    system_prompt = new_prompt


# converting the dataframe into text that could be fed to the LLM
def load_faq_data(faq_path):
    """Load ALL FAQ data as simple text format - no limits"""
    if os.path.exists(faq_path):
        df = pd.read_excel(faq_path, engine='openpyxl')
        df = df.dropna(subset=['Question', 'Answer'])
        
        faq_text = ""
        for i, row in df.iterrows():
            faq_text += f"FAQ {i+1}:\nQ: {row['Question']}\nA: {row['Answer']}\n\n"
        
        return faq_text, df
    else:
        return "", pd.DataFrame(columns=['Question', 'Answer'])
    

# LLM initial setup working 
def LLM_startup(startup_prompt):
    response = gemini_model.generate_content(startup_prompt, 
                                             generation_config=genai.types.GenerationConfig(temperature=0.7,
                                                                                            max_output_tokens=400,
                                                                                            )
                                                                                            )
    return response.text


# LLM response generator 
def LLM_responder(full_prompt):


    
    response = gemini_model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=400,
            )
            )
    return response.text


#-----------------------------------    Initial environment setup     --------------------------------------------- 
faq_text,df = load_faq_data(faq_path)

startup_prompt = f''''
"""
You are Priya, a helpful AI assistant working at Narayan Seva Sansthan.
Greet the user briefly with "Jai Siyaram!" and tell them you can answer questions about our services.
 
short and sweet
Complete Faq Knowledge Base :- 
{faq_text}

'''







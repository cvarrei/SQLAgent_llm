import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json

from SQLAgent import SQLQueryAgent

from langchain.llms import HuggingFaceHub
from langchain.sql_database import SQLDatabase

import warnings
warnings.filterwarnings('ignore')


# Clé à entrer dans le menu latéral pour se connecter à l'API de HuggingFace :    
hf_api_key = st.sidebar.text_input('Clé API HuggingFace', type='password') 
    
    # On indique le modèle de LLM
repo_id = "mistralai/Mixtral-8x7B-Instruct-v0.1"

st.title('Q/ABot 🗣️')
st.toast('Here you can chat with Oliver')
st.markdown("Bienvenue dans la partie 2.0 de notre application ! A votre tour d'être créatif et de poser les questions qui vous tarodent! ")
st.markdown("Vous êtes mis en contact avec notre LLM français: Mixtral-8x7B !")

# On affiche le Q/Abot qu'à la présence de la clé d'accès respectant le format requis
if hf_api_key.startswith('hf_') and len(hf_api_key) == 37:
        st.header("Notre module de Question/Réponse")
        # On crée un formulaire d'envoie
        with st.form('my_form'):
            query = st.text_area('Quelle est votre question?', '')

            if not hf_api_key.startswith('hf_') and len(hf_api_key) != 37:
                st.warning('Entrez une 🤗 HuggingFace API key!', icon='⚠️')
            else:
                st.success("Thanks for the key! ", icon='🤖')
                llm = HuggingFaceHub(
                        repo_id=repo_id,
                        huggingfacehub_api_token=hf_api_key,
                        model_kwargs={"temperature": 0.2, "max_new_tokens": 400}
                    )
                
                MyAgent = SQLQueryAgent(llm=llm, db="sqlite:///database.db")

                # On crée un bouton pour envoyer la question
                submitted = st.form_submit_button('Submit')
                # Si le bouton est cliqué,
                if submitted:
                    # Si la question n'est pas vide,
                    if len(query) == 0:
                        st.error("Attention votre requête est vide !")
                    else:
                        try:
                            # On récupère la réponse à la question
                            result = MyAgent.process_query(query, verbose=True)
                            print(f'Sortie: {result}')
                            # On affiche la réponse
                            st.markdown(result)
                        except Exception as e:
                            # On renvoie un message d'erreur si le Q/Abot n'a pas pu répondre (question trop complexe ou non présente dans la base de donnée)
                            st.error('Je n\'ai pas réussi à répondre a votre question...', icon="🚨")
                            st.text("1) Vérifiez que votre clé API est correcte; 2) Essayez de reformuler votre réponse pour qu'elle soit plus claire")
                    

                st.markdown("Je ne suis qu'un ChatBot étudiant, je n'ai pas encore été dopé ! Mes réponses peuvent tarder jusqu'à 20-30 secondes, soyez patient!\
                            Plus vous serez clair dans votre question, plus je serais rapide et plus je serais également précis dans ma réponse. N'hésitez pas à reformuler vos questions ou les rendre plus détaillé, surtout les plus complexes.")
                st.markdown("Attention, la base de donnée contient le département et la région de l'offre (pas la ville). Elle répondra donc toujours sur le département ou la région de la ville si cette dernière est précisée.")
                st.markdown("**Exemple de questions:**")
                st.caption('Le salaire d\'un data analyst est il plus élevé à Paris ou Lyon?')
                st.caption('Quel est le nombre d\'offres de data scientist à Lyon?')
            st.caption("Existe-t-il des offres de stage à Lille?")
else: 
    st.error("Veuillez rentrer une clé d'accès HuggingFace pour pouvoir faire apparaître le Q/Abot.")    

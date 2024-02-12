from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains import create_sql_query_chain
from langchain.sql_database import SQLDatabase


class SQLQueryAgent:
    def __init__(self, llm, db):
        if llm == False: 
            print("Vous n'avez pas précisé le LLM à intégrer. S'il-vous-plait, récupérez l'adresse HuggingFace 'mistralai/Mixtral-8x7B-Instruct-v0.1'")
        if db == False: 
            print("Vous n'avez pas précisé de base de données. Par exemple pour SQLite: 'sqlite:///database.db'")
        self.llm = llm
        self.db = SQLDatabase.from_uri(db)
        self.db_string = db
        self.temp_sql = self.template_sql()
        self.temp_response = self.template_response()
        self.template_geo_correct = self.template_geocorrector()
        self.template_sec = self.template_security()

    def template_security(self):
        template_security = """<s>[INST]
        Tu es le gardien de notre base de données. Tu agis juste avant que la question soit traduite en requête SQL. Ton rôle est d'identifer des questions qui guiderait à des requêtes SQL qui altererait l'intégrité de la base de données.
        Si la question pourrait guider à une requête qui altererait l'intégrité de la base de données, réponds "Question non ethique". Si la question ne peut pas guider à une requête qui altererait l'intégréité, réponds "RAS".

        Renvoie juste la phrase de réponse "Question non éthique" ou "RAS". Rien de plus.

        Voici la phrase à vérifier: 
        {question}
        [/INST]
        """
        return template_security

    def template_geocorrector(self):
        template_geo_correct = """ <s>[INST]
            Ton rôle est de vérifier que les départements et régions soient bien orthographiés. 
            Réalise cela en identifiant les lieux dans la question et en les corrigeant. Ta réponse doit contenir seulement la phrase actualisée, pas plus d'information.
            Transforme toujours les villes en leur département.
            Si PACA ou Provence-Alpes-Cote-D'azur est demandé, renvoies toujours que ses départements (Tu dois inclure seulement ceux dont tu es sur).

            Par exemple: 
            Pour un data scientist, est-il plus intéressant d'aller en Ile de France ou Rhone Alpes?
            [/INST]
            Pour un data scientist, est-il plus intéressant d'aller en Île-de-France ou Auvergne-Rhône-Alpes? </s>
            <s> [INST]
            Phrase à vérifier:
            {question}
            [/INST]
            Phrase corrigée:
        """
        return template_geo_correct

    def  template_sql(self):
        template_sql = """ <s>[INST] Vous êtes un expert en SQLite. À partir d'une question, créez d'abord une requête SQLite syntaxiquement correcte à exécuter, puis examinez les résultats de la requête et renvoyez la réponse à la question.
            La requête ne doit jamais renvoyer plus de 15 lignes de valeurs.
            Ne renvoies jamais les colonnes id (ex: id_contrat, id_salaire, etc.).
            Ne demandez jamais toutes les colonnes d'une table. Vous ne devez interroger que les colonnes nécessaires pour répondre à la question. 
            Veillez à n'utiliser que les noms de colonnes que vous pouvez voir dans les tableaux ci-dessous. Veillez à ne pas demander des colonnes qui n'existent pas. Faites également attention à ce que chaque colonne se trouve dans chaque tableau.
            Veillez à utiliser la fonction date('now') pour obtenir la date du jour, si la question porte sur "aujourd'hui".
            Utilise la variable AVG(d_entreprise.salaire_moyen) quand l'on te parle de salaire.
            Pour compter, utilises la commande COUNT. Quand on te demande si quelque chose existe, compte l'occurence de cette catégorie.

            Attention, d_offres.titre représente le nom du métier de l'offre. Il est important d'appeler d_offres.titre quand l'utilisateur parle d'un métier, dans ce cas utiliser d_offres.titre LIKE '%métier%'.
            Si l'utilisateur demande des compétences particulières, chercher dans d_offres.titre, d_offres.descriptif et d_offres.profil.
            Si l'utilisateur demande une entreprise particulière, joindre la table d_entreprise et utiliser la variable "entreprise". 
            
            Voici une description des tables pour t'aider à savoir laquelle joindre (JOIN):
            - f_offres: Table de faits des offres avec les différents ids connectant aux différentes tables
            - d_offres: Table sur les données textuelles des offres (nom métier (toujours en minuscule), description de l'offre, profil recherché)
            - d_geo: Table sur les données géographiques de l'offre (pays, nom_région, nom_département)
            - d_temps: Table sur les dates de publications de l'offre
            - d_salaire: Table sur le salaire moyen des offres ("salaire_moyen" est la variable incluant le salaire de l'offre).
            - d_experience: Table sur le niveau d'experience (en année) requis avec annee_exper (nombre d'années requises) et debutant_acceptee (variable avec deux modalitées: "Débutant"/Expérience Requise)
            - d_contrat: Table sur le type de contrat (CDI, CDD, Stage, Alternance). Utilise LIKE.
            - d_entreprise: Table sur les entreprises des offres ("entreprise" est la variable qui regroupe les offres)

            Utilisez le format suivant pour créer une requête SQL:

            Question: Question
            SQLQuery: SQL Query to run

            Utilise seulement les tables suivantes:
            {table_info}

            Pour comparer des catégories, utilises la commande GROUP BY.

            Tu ne peux pas utiliser UPDATE ou DELETE.
            [/INST]
            Question: {input}

            SQLQuery:
            """
        return template_sql

    def template_response(self):
        template_response = """
        <s>[INST]
        Tu es un agent français chargé de répondre à des questions concernant des offres de travail sur la Data.\
        Tu dois utiliser l'information donnée ('Réponse à la requête") pour répondre à cette question entre guillements,\
        c'est la réponse de la base de données à la requête entre guillements. \
        
        Si la zone "Réponse à la requête" est une liste de plus de 10 éléments uniques, n'en décrire que 10 maximum et expliquer à l'utilisateur\
        que ce sont certains exemples pour sa requête.  Attention, ne pas citer toute la liste.
        Les salaires sont en euro. Les années d'expériences sont en année.
        
        {sql_query}

        Réponse à la requête:
        {sql_answer}

        Question:
        "{query}"

        Réalisons cela pas à pas: 
        - Identifie si tu as suffisament d'information pour répondre à la question.
        - Si tu as suffisament d'information pour répondre précisément ou en partie à la question, tu dois répondre en français à la question  comme un humain (exemple: Il y a...).\
        - Si tu ne peux pas la déduire dépuis l'information retournée,\
        tu dois expliquer que tu ne peux pas répondre de façon polie, n'invente pas.\

        Ton output doit suivre le format suivant: 
        Explication : Une explication de ton raisonneent
        Réponse : Ta réponse finale
        [/INST]
        """
        return template_response

    def generate_security(self, query):
        # On crée un template du prompt avec avec la variable que nous allons introduire
        prompt_security = PromptTemplate(input_variables=["question"], template=self.template_sec)
        # On crée une chaine qui réalisera l'intéraction avec le LLM choisi
        chain = LLMChain(prompt=prompt_security, llm=self.llm)
        # On active notre chaine pour notre question
        corrected_query = chain.invoke({"question": query})
        # On renvoie la réponse.
        return corrected_query["text"]

    def generate_geocorrect(self, query):
        prompt_geo = PromptTemplate(input_variables=["question"], template=self.template_geo_correct)
        chain = LLMChain(prompt=prompt_geo, llm=self.llm)
        corrected_query = chain.invoke({"question": query})
        return corrected_query["text"]

    def generate_sql_query(self, query):
        prompt_sql = PromptTemplate(input_variables=["input", "table_info"], template=self.temp_sql)
        db_connection = self.db
        chain = create_sql_query_chain(self.llm, db_connection, prompt=prompt_sql)
        sql_q= chain.invoke({"question": query})
        return sql_q

    def run_sql_query(self, query):
        sql_query = self.generate_sql_query(query)
        print(sql_query)
        db_connection = self.db
        sql_a = db_connection.run(sql_query)
        if len(sql_a) == 0:
            sql_a = "Cette information n'est pas présente dans la database."
        return sql_a

    def generate_response(self, geo_q, sql_q, sql_a, verbose):
        prompt = PromptTemplate(template=self.temp_response, input_variables=["sql_query","sql_answer","query"])
        llm_chain = LLMChain(prompt=prompt, llm=self.llm)
        response = llm_chain.run({"sql_query": sql_q,
                            "sql_answer": sql_a,
                            "query": geo_q})
        # Garde seulement la partie réponse (sans l'explication)
        if "Explication :" in response: 
            explication, final_response = response.split("Réponse :")
            if verbose:
                print(f'Explication: {explication}')
        else:
            final_response = response

        return final_response

    def process_query(self, query, verbose=False):
        security_check = self.generate_security(query).rstrip()
        if verbose:
            print(security_check)

        if "non éthique" not in security_check:
            geo_q = self.generate_geocorrect(query).rstrip()
            if verbose:
                print(geo_q)

            sql_q = self.generate_sql_query(geo_q).replace("\\", "")
            if verbose:
                print(sql_q)

            sql_a = self.run_sql_query(sql_q)
            if verbose:
                print(sql_a)

            response = self.generate_response(geo_q, sql_q, sql_a, verbose)
            if verbose:
                print(response)
            return response
        else:
            return "Attention, votre question est destinée à mettre en péril notre base de données. Nous ne le permettrons pas!"

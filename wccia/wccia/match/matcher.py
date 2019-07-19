# -*- coding: utf-8 -*-

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
# from nltk.corpus import stopwords
# import nltk
# nltk.download('stopwords')
#import spacy
#nlp = spacy.load('en_core_web_sm')
#from pymongo import MongoClient
import numpy as np

class Match(object):
    '''Match instance allows to compare the similarity of instances'''

    def __init__(self):
        #self.server = server
        #self.port = port
        #self.password = password
        self.threshold = 0.85 # default

    def set_threshold(self, value):
        if isinstance(value, float):        
            self.threshold = value
        else:
            raise ValueError('float only')

    def get_threshold(self):
        return self.threshold

    #def get_email_data(self, _id):
    #    '''Retorna informações sobre uma RFQ do banco

    #        Parameters:
    #        _id: identifidor da rfq.

    #        Output:
    #        Cursor com as infos sobre a rfq
    #    '''
        
    #    conn = MongoClient(self.server + ':' + self.port)    
    #    db = conn.emailClassifier
    #    match = db.quotations.find({ "_id":_id }, {"_id":0, "in_reply_to":1, "references":1, "message_ID":1, "sender":1, "receiver":1, "subject":1, "date":1} )

    #    return match

    #def get_data_from_bd(self):
    #    '''
    #    Retorna um vetor com todos as infos dos campos selecionados de todo o banco: subject, body, attch
        
    #    '''
    #    vecs = []        
        
    #    conn = MongoClient(self.server + ':' + self.port)    
    #    db = conn.emailClassifier
        
    #    for record in db.quotations.find( {}, { "subject":1, "anexos.body_txt":1, "anexos.attchs":1 } ):                    
    #            vecs.append([record["_id"], record["subject"], record["anexos"]["body_txt"],record["anexos"]["attchs"] ]) 

    #    return vecs

    #def match_file(self, new_sample):
    #    '''
    #    Compara uma entrada com todas as instancias do banco e gera uma porcentagem de semelhança para cada uma.

    #    Parameter:
    #        new_sample: texto de entrada para comparação.
    #    Output:
    #        lista de IDs de banco dos objetos que estão acima do valor de corte $cut_value   
    #    '''
    #    matches = []
    #    all_vecs = self.get_data_from_bd() #busca todas as instancias de RFQs no BD
        
    #    for inst in all_vecs:

    #        inst_text = inst[1].decode() #o body da instancia do banco precisa ser decodificado (esta em bytes)
                        
    #        values_matrix = self.get_tf_idf(new_sample, inst_text) 

    #        result = values_matrix[0][1]

    #        if(result >= self.get_threshold()): #se esta acima do valor de corte            
    #            matches.append(self.get_email_data(inst[0])) #resgata dados do objeto do BD.
    #            print(result)
                       
    #    self.show_match(matches) #exibe os emails similares
            
    #def show_match(self, lista):
    #    ''''''
    #    for j in range(len(lista)):
    #        for i in lista[j]:
    #            print(i)
        
    #def extract_data(self, file):
    #    """Extrai o texto de um arquivo.

    #    # Arguments
    #        file: arquivo texto

    #    # Output
    #        string
    #    """
    #    sample = ""
    #    with open(file) as myfile:
    #        for line in myfile.readlines():
    #            line = re.sub("[\n\r']", "", line)
    #            if len(line) != 0:
    #                sample = sample + line
    #    return sample

    def get_jaccard_sim(self, str1, str2):
        """Mede a similaridade pela métrica de jaccard"""
        a = set(str1.split()) 
        b = set(str2.split())
        c = a.intersection(b)
        return float(len(c)) / (len(a) + len(b) - len(c))

    def get_embedding_sim(self, *strs):        
        """Mede a similaridade com de embedded words e metrica coseno"""
        vectors = [t for t in self.get_embedding_vectors(*strs)]
        return np.round(cosine_similarity(vectors), 2)
        
    def get_embedding_vectors(self, *strs):
        '''Vetoriza as instancias pelo método de embedding words'''
        #stopWords = stopwords.words('english')        
        text = [t for t in strs]
        vectorizer = CountVectorizer(text)        
        vectorizer.fit(text)

        return vectorizer.transform(text).toarray()

    def get_tf_idf(self, *strs):
        '''Vetoriza as instancias pelo método tf-idf'''
        #stopWords = stopwords.words('english')
        vectors = [t for t in strs]    
        tfidf = TfidfVectorizer(max_features = 6000, ngram_range=(1, 1))        
        tfidf_features = tfidf.fit_transform(vectors).toarray()        
        return np.round(cosine_similarity(tfidf_features), 2)

    # def get_spacy_sim(self, doc1, doc2):        
    #     doc1 = nlp(doc1)
    #     doc2 = nlp(doc2)        
    #     return np.round(doc1.similarity(doc2), 2)


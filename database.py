import cv2
from datetime import date, datetime
import os
import sqlite3 as sql
import threading
import sys

class Database:
    def __init__(self):
        self.db_lock = threading.Lock()

    def upload_image(self, real_img, img, user_id, prediction):
        path = 'uploads/'+user_id + '/'
        isExist = os.path.exists(path)
        if not isExist:
            os.makedirs(path)
        
        history_index = len(os.listdir("./uploads/"+user_id))  + 1
        folder_path = path + str(history_index) +"/"

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        base_image_path = folder_path + "base_img.jpg"
        result_image_path = folder_path + "result_img.jpg"
        cv2.imwrite(base_image_path, real_img)
        cv2.imwrite(result_image_path, img)

        # Insert image to database
        image_id = self.insert_image(base_image_path, result_image_path)
        
        # Insert history to database
        history_id = self.insert_history(history_index, user_id, image_id)

        # Insert history details to database
        self.insert_history_details(history_id, prediction)

        return history_id



    def insert_image(self, base_image_path, result_image_path):
        con = self.get_db_connection()
        cursor = con.cursor()
        cursor.execute('INSERT OR REPLACE INTO images (base_image_path, result_image_path) VALUES (?, ?)',[base_image_path, result_image_path])
        con.commit()

        image_id = cursor.lastrowid
        cursor.close()
        con.close()
        return image_id

    def insert_history_details(self, history_id, prediction):
        print(prediction)
        con = self.get_db_connection()
        for idx, _ in enumerate(prediction):
            print(history_id, (idx + 1), float(prediction[idx]))
            con.execute('INSERT OR REPLACE INTO history_details (history_id, emotion_id, probability) VALUES (?, ? , ?)',[
                history_id, (idx + 1), float(prediction[idx])
            ])
        con.commit()
        con.close()

    def get_history(self, user_id):
        con = self.get_db_connection()
        histories = con.execute('SELECT * FROM histories where user_id = ? order by date DESC', [user_id]).fetchall()
        con.close()
        return histories   

    def get_highest_prob(self, history_id):
        con = self.get_db_connection()
        highest_prob = con.execute('select * from history_details where history_id = ? order by probability desc limit 1', [history_id]).fetchone()

        con.close()
        return highest_prob

    def get_image(self, history_id):
        con = self.get_db_connection()
        image = con.execute('select images.* from images join histories on images.image_id = histories.image_id where history_id = ?', [history_id]).fetchone()
        con.close()
        return image
    
    def get_history_details(self, history_id):
        con = self.get_db_connection()
        history_details = con.execute('select * from history_details where history_id = ? order by probability desc', [history_id]).fetchall()
        con.close()
        return history_details

    def insert_emotions(self, emotion_dict):
        con = self.get_db_connection()
        for idx in emotion_dict:
            con.execute('INSERT OR REPLACE INTO emotions (emotion_name) VALUES (?)',[emotion_dict[idx]])
        con.commit()
        con.close()

    def insert_history(self, history_index, user_id, image_id):
        con = self.get_db_connection()
        cursor = con.cursor()
        cursor.execute('INSERT OR REPLACE INTO histories (history_id, user_id, image_id) VALUES (?, ?, ?)',[history_index, user_id, image_id])
        con.commit()
        history_id = cursor.lastrowid
        cursor.close()
        con.close()
        return history_id
    

    def get_csv_data(self):
        con = self.get_db_connection()
        query = '''
            SELECT histories.history_id, emotion_name, questionnaire.value from emotions, questionnaire, histories,
            (
                SELECT history_id , emotion_id, MAX(PROBABILITY)
                FROM history_details
                GROUP BY history_id
            ) AS MAX_VAL
            WHERE histories.history_id = MAX_VAL.history_id
            AND EMOTIONS.emotion_id = MAX_VAL.emotion_id
            AND histories.history_id = questionnaire.history_id

            '''
        rows = con.execute(query).fetchall()

        con.close()
        return rows


    def init_database(self, emotion_dict):

        filename = "./sqlite/database.db"

        if os.path.exists(filename): return

        connection = sql.connect('./sqlite/database.db')

        with open('./sqlite/schema.sql') as f:
            connection.executescript(f.read())
        
        connection.commit()
        connection.close()

        self.insert_emotions(emotion_dict)

    def get_db_connection(self):
        conn = sql.connect('./sqlite/database.db')
        conn.row_factory = sql.Row
        return conn
    

    def add_questionnaire(self, content):
        con = self.get_db_connection()

        print(type(content.get('value')), file=sys.stderr)    
        serialized_data = self.serialize(content.get('value'))

        cursor = con.cursor()
        cursor.execute('INSERT INTO questionnaire (history_id, value) VALUES (?, ?)',[content.get('history_id'), serialized_data])
        con.commit()

        cursor.close()
        con.close()
        return

    def serialize(self, data):
        serialized_data = '#'.join(str(num) for num in data)

        return serialized_data
        


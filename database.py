import cv2
import os
import sqlite3 as sql
import sys
import os
import psycopg2

class Database:
    def __init__(self):
        # self.db_lock = threading.Lock()
        conn = self.get_db_connection()
        
        cur = conn.cursor()
        # cur.execute("DROP TABLE IF EXISTS questionnaire, history_details, histories, emotions, images, users CASCADE;")

        cur.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS images (
            image_id SERIAL PRIMARY KEY,
            image_data BYTEA NOT NULL,
            base_image_path TEXT NOT NULL,
            result_image_path TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS histories (
            history_id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            image_id INTEGER NOT NULL,
            date TIMESTAMP NOT NULL DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON UPDATE CASCADE,
            FOREIGN KEY (image_id) REFERENCES images (image_id) ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS emotions (
            emotion_id SERIAL PRIMARY KEY,
            emotion_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS history_details (
            history_id INTEGER NOT NULL,
            emotion_id INTEGER NOT NULL,
            probability REAL NOT NULL,
            FOREIGN KEY (history_id) REFERENCES histories (history_id) ON UPDATE CASCADE,
            FOREIGN KEY (emotion_id) REFERENCES emotions (emotion_id) ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS questionnaire (
            history_id INTEGER NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (history_id) REFERENCES histories (history_id) ON UPDATE CASCADE
        );''')

        conn.commit()
        cur.close()
        conn.close()

        pass


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
        history_id = self.insert_history(user_id, image_id)

        # Insert history details to database
        self.insert_history_details(history_id, prediction)

        return history_id


    def insert_image(self, base_image_path, result_image_path):
        image_id = self.write_blob(base_image_path, result_image_path)
        return image_id
    
    def write_blob(self, base_image_path, result_image_path):
        image_id = 0  # Initialize image_id
        try:
            # Read data from an image file
            image = open(result_image_path, 'rb').read()

            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("INSERT INTO images (image_data, base_image_path, result_image_path) "
                            "VALUES (%s, %s, %s) RETURNING image_id",
                            (psycopg2.Binary(image), base_image_path, result_image_path))
                
                # Fetch the image_id from the RETURNING clause
                image_id = cursor.fetchone()[0]
                
                conn.commit()
            except (Exception, psycopg2.DatabaseError) as error:
                print("Error while inserting data in the images table:", error)
            finally:
                cursor.close()
        except Exception as e:
            print("Error while reading the image file:", e)
        finally:
            return image_id

    def insert_history_details(self, history_id, prediction):
        print(prediction)
        con = self.get_db_connection()
        cur = con.cursor()
        for idx, _ in enumerate(prediction):
            print(history_id, (idx + 1), float(prediction[idx]))
            cur.execute('INSERT INTO history_details (history_id, emotion_id, probability) VALUES (%s, %s , %s)',[
                history_id, (idx + 1), float(prediction[idx])
            ])
        con.commit()
        cur.close()
        con.close()

    def get_history(self, user_id):
        con = self.get_db_connection()
        cur = con.cursor()
        histories = cur.execute('SELECT * FROM histories where user_id = %s order by date DESC', [user_id]).fetchall()
        con.commit()
        cur.close()
        con.close()
        return histories   

    def get_highest_prob(self, history_id):
        con = self.get_db_connection()
        cur = con.cursor()
        highest_prob = cur.execute('select * from history_details where history_id = %s order by probability desc limit 1', [history_id]).fetchone()

        con.commit()
        cur.close()
        con.close()
        return highest_prob

    def get_image(self, history_id):
        con = self.get_db_connection()
        cursor = con.cursor()
        cursor.execute('select images.* from images join histories on images.image_id = histories.image_id where history_id = %s', [history_id])
        image = cursor.fetchall()[0]
        con.commit()
        cursor.close()
        con.close()
        return image
    
    def get_history_details(self, history_id):
        con = self.get_db_connection()
        cursor = con.cursor()
        cursor.execute('select * from history_details where history_id = %s order by probability desc', [history_id])
        history_details = cursor.fetchall()
        con.commit()
        cursor.close()
        con.close()
        return history_details

    def insert_emotions_if_empty(self, emotion_dict):
        con = self.get_db_connection()
        cur = con.cursor()

        # Check if the 'emotions' table is empty
        cur.execute('SELECT COUNT(*) FROM emotions')
        count = cur.fetchone()[0]

        if count == 0:
            # The table is empty, so insert emotions
            for idx in emotion_dict:
                cur.execute('INSERT INTO emotions (emotion_name) VALUES (%s)', [emotion_dict[idx]])
            con.commit()
        else:
            print("The 'emotions' table is not empty. Skipping insertion.")

        cur.close()
        con.close()


    def insert_history(self, user_id, image_id):
        con = self.get_db_connection()
        cursor = con.cursor()
        cursor.execute('INSERT INTO histories (user_id, image_id) VALUES (%s, %s) RETURNING history_id', [user_id, image_id])
        con.commit()
        history_id = cursor.fetchone()[0]
        cursor.close()
        con.close()
        return history_id

    def get_csv_data(self):
        con = self.get_db_connection()
        cursor = con.cursor()
        query = '''
        SELECT
            h.user_id,
            i.image_data,
            e.emotion_name,
            hd.probability
        FROM
            histories h
        JOIN
            images i ON h.image_id = i.image_id
        JOIN
            history_details hd ON h.history_id = hd.history_id
        JOIN
            emotions e ON hd.emotion_id = e.emotion_id
        '''
        cursor.execute(query)

        rows = cursor.fetchall()

        con.commit()
        cursor.close()
        con.close()
        return rows


    def init_database(self, emotion_dict):
        self.insert_emotions_if_empty(emotion_dict)

    def get_db_connection(self):

        conn = psycopg2.connect(
            host=os.environ.get("DATABASE_HOST"),
            database=os.environ.get("DATABASE_NAME"),
            user=os.environ.get("DATABASE_USER"),
            password= os.environ.get("DATABASE_PASSWORD"),
            port= os.environ.get("DATABASE_PORT")
        )   

        return conn
    

    def add_questionnaire(self, content):
        con = self.get_db_connection()

        print(type(content.get('value')), file=sys.stderr)    
        serialized_data = self.serialize(content.get('value'))

        cursor = con.cursor()
        cursor.execute('INSERT INTO questionnaire (history_id, value) VALUES (%s, %s)',[content.get('history_id'), serialized_data])
        con.commit()

        cursor.close()
        con.close()
        return

    def serialize(self, data):
        serialized_data = '#'.join(str(num) for num in data)

        return serialized_data
        


drop table if exists users;
drop table if exists images;
drop table if exists histories;
drop table if exists history_details;
drop table if exists emotions;
drop table if exists questionnaire;

create table users (
user_id text primary key
);

create table images (
image_id integer primary key autoincrement,
base_image_path text not null,
result_image_path text not null
);

create table histories (
history_id integer primary key,
user_id text not null,
image_id integer not null,
date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (user_id) REFERENCES users (user_id) on update cascade, 
FOREIGN KEY (image_id) REFERENCES images(image_id) on update cascade
);

create table emotions (
emotion_id integer primary key autoincrement,
emotion_name text not null
);

create table history_details (
history_id integer not null,
emotion_id integer not null,
probability real not null,
FOREIGN KEY (history_id) REFERENCES histories (history_id) on update cascade, 
FOREIGN KEY (emotion_id) REFERENCES emotions(emotion_id) on update cascade
);

create table questionnaire (
history_id integer not null,
value text not null,
FOREIGN KEY (history_id) REFERENCES histories (history_id) on update cascade
);
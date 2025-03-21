from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///image.db'
app.config['UPLOAD_FOLDER'] = 'image'
db = SQLAlchemy(app)
api = Api(app)

# Image
class Image(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  url = db.Column(db.String(255), nullable=False)
  created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

  def __repr__(self):
     return f"Image(url = {self.url})"

# Tag Table
class Tag(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100), unique=True, nullable=False)


# Image Tag
class ImageTag(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
  tag_id = db.Column(db.Integer,  db.ForeignKey('tag.id'), nullable=False)
  image = db.relationship('Image', backref=db.backref('image_tags', cascade='all, delete-orphan'))
  tag = db.relationship('Tag', backref=db.backref('image_tags', cascade='all, delete-orphan'))


tag_name_args = reqparse.RequestParser()
tag_name_args.add_argument('name', type=str, required=True, help="Tag Name cannot be blank")

image_tag_args = reqparse.RequestParser()
image_tag_args.add_argument('image_id', type=int, required=True, help="Image ID is required")
image_tag_args.add_argument('tag_ids', type=int, action='append', required=True, help="Tag IDs are required")

## in create_db.py

imageFields = {
   'id':fields.Integer,
   'url':fields.String(255),
   'created_at': fields.DateTime(dt_format='iso8601')
}

tagFields = {
   'id': fields.Integer,
   'name': fields.String(100),
}

imageTagFields = {
    'id': fields.Integer,
    'image_id': fields.Integer,
    'tag': fields.Nested({
        'id': fields.Integer,
        'name': fields.String
    })
}

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Wallpaper API"})

class ImageResource(Resource):
   @marshal_with(imageFields)
   def get(self):
      images = Image.query.all()
      return images


class ImageByIdResource(Resource):
   @marshal_with(imageFields)
   def get(self, id):
      image = Image.query.filter_by(id=id).first()
      if not image:
         abort(404, message="Image not found")
      return image
   
   
class TagResource(Resource):
   @marshal_with(tagFields)
   def get(self):
      tags = Tag.query.all()
      return tags
   
   @marshal_with(tagFields)
   def post(self):
      args = tag_name_args.parse_args()
      tag_name = args['name']
      existing_tag = Tag.query.filter_by(name=tag_name).first()
      if existing_tag:
        return {"message": "Tag already exists."}, 400
      
      tag = Tag(name=tag_name)
      db.session.add(tag)
      db.session.commit()
      return tag, 201
   
class ImageTagResource(Resource):
    def get(self, image_id):
        image_tags = ImageTag.query.filter_by(image_id=image_id).all()
        if not image_tags:
            abort(404, message="No tags found for this image")

        tags = [{"id": it.tag.id, "name": it.tag.name} for it in image_tags]
        return {"image_id": image_id, "tags": tags}, 200

    def post(self):
        args = image_tag_args.parse_args()
        image_id = args['image_id']
        tag_ids = args['tag_ids']

        image = Image.query.get(image_id)
        if not image:
            abort(404, message="Image not found")

        added_tags = []
        for tag_id in tag_ids:
            tag = Tag.query.get(tag_id)
            if not tag:
                continue

            existing_image_tag = ImageTag.query.filter_by(image_id=image_id, tag_id=tag_id).first()
            if not existing_image_tag:
                image_tag = ImageTag(image_id=image_id, tag_id=tag_id)
                db.session.add(image_tag)
                added_tags.append({"id": tag.id, "name": tag.name})

        db.session.commit()
        
        if not added_tags:
            abort(400, message="No new tags were added")

        return {"message": "Tags added successfully", "tags": added_tags}, 201

api.add_resource(ImageResource, '/api/images')
api.add_resource(ImageByIdResource, '/api/detail/<int:id>')
api.add_resource(TagResource, '/api/tags')
api.add_resource(ImageTagResource, '/api/image-tags/<int:image_id>', '/api/image-tags')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run()

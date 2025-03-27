from flask import Flask, request, jsonify, send_from_directory, json
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///image.db'
app.config['UPLOAD_FOLDER'] = 'image'

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

db = SQLAlchemy(app)
api = Api(app)
CORS(app)

def allowed_file(filename):
   return '.'in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

image_url_args = reqparse.RequestParser()
image_url_args.add_argument('url', type=str, required=True, help="Image URL cannot be blank")

tag_name_args = reqparse.RequestParser()
tag_name_args.add_argument('name', type=str, required=True, help="Tag Name cannot be blank")

image_tag_args = reqparse.RequestParser()
image_tag_args.add_argument('image_id', type=int, required=True, help="Image ID is required")
image_tag_args.add_argument('tag_ids', type=int, action='append', required=True, help="Tag IDs are required")

## in create_db.py

imageFields = {
   'id':fields.Integer,
   'url':fields.String,
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
      print(Image.query.all().count) 
      images = Image.query.all()
      print(images)
      return images
   
   
   def post(self):
    if not request.is_json:
        return {"message": "Request must be JSON"}, 400 

    args = request.get_json() 
    url = args.get('url')
    image_url = Image(url=url)
    db.session.add(image_url)
    db.session.commit()

    return image_url, 201
      


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
    
    def delete(self, image_id, tag_id):
        image_tag = ImageTag.query.filter_by(image_id=image_id, tag_id=tag_id).first()

        if not image_tag:
            return {"message": "Tag not found for this image"}, 404

        db.session.delete(image_tag)
        db.session.commit()

        return {"message": "Tag deleted successfully"}, 200


api.add_resource(ImageResource, '/api/images')
api.add_resource(ImageByIdResource, '/api/detail/<int:id>')
api.add_resource(TagResource, '/api/tags')
api.add_resource(ImageTagResource, '/api/image-tags/<int:image_id>', '/api/image-tags', '/api/image-tags/<image_id>/<tag_id>')


@app.route('/api/images/upload', methods=['POST']) 
@marshal_with(imageFields)
def upload_image():
    args = image_url_args.parse_args()
    image_url = args['url']
    exsited_url = Image.query.filter_by(url = image_url).first()
    if exsited_url:
        return {"message": "Image already exists."}, 400
    
    url = Image(url = image_url)
    db.session.add(url)
    db.session.commit()
    return {"Image added successfully"}, 201


    # if 'image' not in request.files:
    #   return {"message": "No file part in the request"}, 400
   
    # files = request.files.getlist('image')

    # error = {}
    # success = False
    # uploaded_urls = []

    # for file in files:
    #     if file and allowed_file(file.filename):
    #         filename = secure_filename(file.filename)
    #         file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    #         file.save(file_path)

    #         image_url = f"{request.host_url}{app.config['UPLOAD_FOLDER']}/{filename}"
    #         new_image = Image(url = image_url)
    #         db.session.add(new_image)
    #         db.session.commit()
    #         success = True
    #         uploaded_urls.append(image_url)
    #     else: 
    #         error[file.filename] = "File type is not allowed"

    # if success and error:
    #     error['message'] = "Some files were uploaded successfully, but some had errors"
    #     return jsonify({"uploaded": uploaded_urls, "errors": error}), 207 
    # elif success:
    #     return jsonify({"message": "File(s) successfully uploaded", "uploaded": uploaded_urls}), 201
    # else:
    #     return jsonify({"errors": error}), 400
    
@app.route('/api/images/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    image = Image.query.get(image_id)

    if not image:
        return {"message": "Image not found"}, 404

    # filename = os.path.basename(image.url)
    # file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # if os.path.exists(file_path):
    #     os.remove(file_path)

    db.session.delete(image)
    db.session.commit()

    return {"message": "Image deleted successfully"}, 200

    
      
# def upload_image():
#     try:
#         args = tag_name_args.parse_args()
#         tag_name = args['name']

#         existing_tag = Tag.query.filter_by(name=tag_name).first()
#         if existing_tag:
#             return {"message": "Tag already exists."}, 400

#         tag = Tag(name=tag_name)
#         db.session.add(tag)
#         db.session.commit()

#         return tag, 201
#     except Exception as e:
#         return {"error": str(e)}, 500



if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run()

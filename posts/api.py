import json

from flask import request, Response, url_for
from jsonschema import validate, ValidationError

import models
import decorators
from posts import app
from database import session

# JSON Schema describing the structure of a post
post_schema = {
    "properties": {
        "title" : {"type" : "string"},
        "body": {"type": "string"}
    },
    "required": ["title", "body"]
}

@app.route("/api/posts", methods=["GET"])
@decorators.accept("application/json")
def posts_get():
    """ Get a list of posts """
    # Get the querystring arguments
    title_like = request.args.get("title_like")
    body_like = request.args.get("body_like")

    # Get and filter the posts from the database
    posts = session.query(models.Post)
    if title_like:
        posts = posts.filter(models.Post.title.contains(title_like))
    elif body_like:
        posts = posts.filter(models.Post.body.contains(body_like))
    elif title_like and body_like: # Title takes precedence in the filtering with this setup
        # First this filters for all the posts with the title requested
        posts = posts.filter(models.Post.title.contains(title_like))
        # Then the remaining posts are filtered for the body requested
        posts = posts.filter(models.Post.body.contains(body_like))
    # Then we use the query we setup above with the filter triggered and assign those to posts.
    posts = posts.all()

    # Convert the posts to JSON and return a response
    data = json.dumps([post.as_dictionary() for post in posts])
    return Response(data, 200, mimetype="application/json")

@app.route("/api/posts/<int:id>", methods=["GET", "PUT"])
@decorators.accept("application/json")
def post_get(id):
    """ Single post endpoint """
    # Get the post from the database

    # create a conditional for GET and PUT
    if request.method == "GET":
        post = session.query(models.Post).get(id)

        # Check whether the post exists
        # If not return a 404 with a helpful message
        if not post:
            message = "Could not find post with id {}".format(id)
            data = json.dumps({"message": message})
            return Response(data, 404, mimetype="application/json")
    elif request.method == "PUT":
        # assigning the data to the variable 'post'
        post = session.query(models.Post).get(id)
        # printing the data to debug using repr. This will print the data in a string
        # print "Request.data is: ", repr(request.data)
        # Since the data is coming in as a json, use json.loads to create a python dictionary with it
        # Assign the data in dictionary form, to a variable to use. In this case req_d
        req_d = json.loads(request.data)
        # Assign the post.title and post.body from the new info passed in
        post.title = req_d["title"]
        post.body =  req_d["body"]
        # commit the changes since the data is "in transit" at this time.
        session.commit()
    else:
        message = "This is not a valid HTTP method"
        data = json.dumps({"message": message})
        return Response(data, 500, mimetype="application/json")

    # Return the post as JSON
    data = json.dumps(post.as_dictionary())
    return Response(data, 200, mimetype="application/json")

@app.route("/api/posts", methods=["POST"])
@decorators.accept("application/json")
@decorators.require("application/json")
def posts_post():
    """ Add a new post """
    data = request.json

    # Check that the JSON supplied is valid
    # If not we return a 422 Unprocessable Entity
    try:
        validate(data, post_schema)
    except ValidationError as error:
        data = {"message": error.message}
        return Response(json.dumps(data), 422, mimetype="application/json")

    # Add the post to the database
    post = models.Post(title=data["title"], body=data["body"])
    session.add(post)
    session.commit()

    # Return a 201 Created, containing the post as JSON and with the
    # Location header set to the location of the post
    data = json.dumps(post.as_dictionary())
    headers = {"Location": url_for("post_get", id=post.id)}
    return Response(data, 201, headers=headers,
                    mimetype="application/json")


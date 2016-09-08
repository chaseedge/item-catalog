from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, make_response
from sqlalchemy import create_engine, asc
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Genre, Movie, User, Review
from flask import session as login_session
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import re

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

app = Flask(__name__)

# Connect to Database and create database session
engine = create_engine('sqlite:///moviecatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def getUser(user_id):
    return session.query(User).filter_by(id=user_id).one()


def getUserByEmail(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user
    except:
        return None


def createUser(login_session, pw_hash=None):
    newUser = User(
        name=login_session['username'],
        email=login_session['email'],
        pw_hash=pw_hash)
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user


def createMovie(
        user_id,
        genre_id,
        title,
        description=None,
        year=None,
        poster=None,
        backdrop=None,
        actor_list=None,
        trailer=None,
        tmdb_id=None):
    if title:
        movie = Movie(
            user_id=user_id,
            genre_id=genre_id,
            title=title,
            description=description,
            tmdb_id=tmdb_id,
            year=year,
            poster=poster,
            backdrop=backdrop,
            actor_list=actor_list,
            trailer=trailer)
        session.add(movie)
        session.commit()
        return movie
    print 'name needed to create a movie'


def getAllGenres():
    genres = session.query(Genre).all()
    for genre in genres:
        if session.query(Movie).filter_by(genre_id=genre.id).count() == 0:
            session.delete(genre)
            session.commit()
    genres = session.query(Genre).all()
    return genres


def getGenreById(genre_id):
    genre = session.query(Genre).filter_by(id=genre_id).one()
    return genre


# will add genre if it doesn't exist
def getGenreByName(name):
    name = name.lower()
    try:
        genre = session.query(Genre).filter_by(name=name).one()
    except:
        genre = Genre(name=name)
        session.add(genre)
        session.commit()
    return genre


def getMovie(movie_id):
    movie = session.query(Movie).filter_by(id=movie_id).one()
    return movie


def getReviews(movie_id):
    reviews = session.query(Review).filter_by(movie_id=movie_id).all()
    return reviews

# updates the movie rating


def updateRating(movie_id):
    movie = getMovie(movie_id)
    reviews = getReviews(movie_id)
    num = session.query(Review).filter_by(movie_id=movie_id).count()
    sum = 0
    for review in reviews:
        sum += review.rating
    if num > 0:
        rating = 1.0 * sum / num
        movie.rating = round(rating, 1)
    else:
        movie.rating = None
    session.add(movie)
    session.commit()
    return movie


@app.template_filter('rating')
def getRatingFilter(movie_id):
    reviews = session.query(Review).filter_by(movie_id=movie_id).all()
    num = session.query(Review).filter_by(movie_id=movie_id).count()
    rating = None
    sum = 0
    for review in reviews:
        sum += review.rating
    if num > 0:
        rating = 1.0 * sum / num
    return rating


# filters to look up Genre and User names
@app.template_filter('genre_name')
def genreNameFilter(genre_id):
    genre = getGenreById(genre_id)
    return genre.name


@app.template_filter('username')
def usernameFilter(user_id):
    user = getUser(user_id)
    return user.name


@app.template_filter('genre_count')
def getGenreCount(genre_id):
    num = session.query(Movie).filter_by(genre_id=genre_id).count()
    return num

# filters for the different poster sizes

# check to see if poster is from TheOpenMovieDB and then select size


@app.template_filter('small_poster')
def getSmallPoster(s):
    try:
        if s[:1] == "/":
            url = "http://image.tmdb.org/t/p/w185%s" % s
            return url
    except:
        return s

# check to see if poster is from TheOpenMovieDB and then select size


@app.template_filter('big_poster')
def getBigPoster(s):
    print 'first letter is ', s[:1]
    url = "http://image.tmdb.org/t/p/w640%s" % s
    return url


@app.template_filter('format_datetime')
def formatDatetime(t):
    return t.strftime("%m/%d/%Y at %I:%M %p")


@app.errorhandler(404)
def pageNotFound(e):
    return render_template('404.html'), 404


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if 'username' in login_session:
        login_session.clear()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        verify = request.form['verify']
        error = None

        if not username or not email or not password:
            flask('all fields are required')
            error = True

        if getUserByEmail(email):
            flash('that email has already been taken')
            error = True

        validEmail = re.match(
            '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email)
        if not validEmail:
            flask('valid email is required')
            error = True

        if verify != password:
            flask('passwords do not match')
            error = True

        if error:
            return render_template(
                'signup.html', username=username, email=email)

        login_session['username'] = username
        login_session['email'] = email

        pw_hash = generate_password_hash(password)
        user = createUser(login_session, pw_hash)
        if user:
            login_session['user_id'] = user.id
            flash("Account created for %s" % user.name)
        return redirect(url_for('showCatalog'))

    return render_template('signup.html')

# login handler with anti-forgery state token


@app.route('/login', methods=["POST", "GET"])
def showLogin():
    if request.method == "POST":

        # check to see if already logged in and then logout user
        if 'provider' in login_session:
            if login_session['provider'] == 'facebook':
                fbdisconnect()
        if 'username' in login_session:
            login_session.clear()

        email = request.form['email']
        password = request.form['password']

        user = getUserByEmail(email)
        if not user:
            flash("Sorry, there is no account associated with this email")
            return render_template('login.html')

        if check_password_hash(user.pw_hash, password):
            login_session['username'] = user.name
            login_session['email'] = user.email
            login_session['user_id'] = user.id
            flash("Welcome back %s" % user.name)
            return redirect(url_for('showCatalog'))
        else:
            flash("Sorry, incorrect password")
            return render_template('login.html', email=email)

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter/'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data

    # Exchange client token for long-lived server-side token with
    # GET/oauth/access_token
    app_id = json.loads(
        open(
            'fb_client_secrets.json',
            'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = 'https://graph.facebook.com/v2.2/me'
    # Strip expire tag from access_token
    token = result

    url = 'https://graph.facebook.com/v2.2/me?fields=name,email,picture&%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]
    login_session['picture'] = data["picture"]["data"]["url"]
    login_session['provider'] = 'facebook'

    # see if user exists in User db
    user = getUserByEmail(login_session['email'])
    if not user:
        user = createUser(login_session)
    login_session['user_id'] = user.id

    return login_session['username']


# check to see if logged into facebook then check other login
@app.route('/logout')
def logout():
    if 'provider' in login_session:
        if login_session['provider'] == 'facebook':
            fbdisconnect()
        login_session.clear()
        flash("You have been logged out.")
        return redirect(url_for('showCatalog'))

    if 'username' in login_session:
        login_session.clear()
        return redirect(url_for('showCatalog'))
    else:
        flash('You were not logged in to begin with')
        return redirect(url_for('showCatalog'))


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    url = 'https://graph.facebook.com/%s/permissions' % facebook_id
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/')
@app.route('/catalog/')
def showCatalog():
    movies = session.query(Movie).all()
    genres = getAllGenres()
    return render_template('catalog.html', movies=movies, genres=genres)


@app.route('/catalog/JSON')
@app.route('/catalog/json')
def showCatalogJSON():
    genres = getAllGenres()
    for genre in genres:
        movies = session.query(Movie).filter_by(genre_id=genre.id).all()
        genre.movies = [movie.serialize for movie in movies]
        genre.json = {
            'id': genre.id,
            'genre': genre.name,
            'movies': genre.movies
        }
    movies = session.query(Movie).group_by(Movie.genre_id).all()
    return jsonify(Genres=[g.json for g in genres])


# Shows top rated movies
@app.route('/catalog/top/')
def showTop():
    movies = session.query(Movie).filter(
        Movie.rating > 0).order_by(
        Movie.rating.desc()).all()
    genres = getAllGenres()
    return render_template('catalog.html', movies=movies, genres=genres)

# shows recently added movies


@app.route('/catalog/recent/')
def showRecent():
    movies = session.query(Movie).order_by(Movie.added_on.desc()).limit(5)
    return render_template('recent.html', movies=movies)


@app.route('/catalog/genre/<name>/')
def showGenre(name):
    if session.query(Genre).filter_by(name=name).count() == 0:
        flash("Sorry, the genre %s does not exist" % name)
        return redirect(url_for('showCatalog'))
    genre = getGenreByName(name)
    movies = session.query(Movie).filter_by(genre_id=genre.id).all()
    genres = session.query(Genre).all()
    return render_template(
        'showGenre.html',
        movies=movies,
        genre=genre,
        genres=genres)


@app.route('/catalog/movies/<int:movie_id>/')
def showMovie(movie_id):
    # Check to see if the user has reviewed the movie already.
    if 'username' in login_session:
        user = session.query(User).filter_by(id=login_session['user_id']).one()

        user_review = session.query(Review).filter_by(
            movie_id=movie_id, user_id=user.id).count()

    reviews = session.query(Review).filter_by(movie_id=movie_id).all()
    movie = getMovie(movie_id)
    genres = getAllGenres()
    return render_template(
        'showMovie.html',
        movie=movie,
        user=user,
        reviews=reviews,
        genres=genres,
        user_review=user_review)


@app.route('/catalog/movies/<int:movie_id>/JSON')
@app.route('/catalog/movies/<int:movie_id>/json')
def showMovieJSON(movie_id):
    movie = getMovie(movie_id)
    reviews = getReviews(movie_id)
    reviews_JSON = [review.serialize for review in reviews]
    movie.json = {
        'movie': movie.serialize,
        'reviews': reviews_JSON
    }
    return jsonify(movie.json)


@app.route('/catalog/movies/new', methods=['GET', 'POST'])
def newMovie():
    if 'username' not in login_session:
        flash('You must login in order to add a movie')
        return redirect(url_for('showLogin'))
    genres = getAllGenres()
    if request.method == 'POST' and 'user_id' in login_session:
        user_id = login_session['user_id']
        title = request.form['title']
        year = request.form['year']
        poster = request.form['poster']
        trailer = request.form['trailer']
        actor_list = request.form['actor_list']
        backdrop = request.form['backdrop']
        description = request.form['description']
        genre_id = request.form['genre']
        if genre_id == 'other':
            name = request.form['other']
            genre = getGenreByName(name)
            genre_id = genre.id
        if title == "" or not genre_id:
            flash("Movie title and genre required")
            return render_template('newMovie.html', genres=genres)
        movie = createMovie(
            user_id,
            genre_id,
            title,
            description,
            year,
            poster,
            backdrop,
            actor_list,
            trailer)
        return redirect(url_for('showMovie', movie_id=movie.id))
    else:
        return render_template('newMovie.html', genres=genres)


@app.route('/catalog/movies/<int:movie_id>/edit/', methods=['GET', 'POST'])
def editMovie(movie_id):
    movie = getMovie(movie_id)
    user = getUser(movie.user_id)
    if login_session['user_id'] != movie.user_id:
        flash('Only %s can make changes to this movie' % user.name)
        return redirect(url_for('showMovie', movie_id=movie.id))

    genres = getAllGenres()
    movie = getMovie(movie_id)
    if request.method == 'POST':
        movie.title = request.form['title']
        movie.year = request.form['year']
        movie.poster = request.form['poster']
        movie.trailer = request.form['trailer']
        genre_id = request.form['genre']

        # check and see if other was listed as genre and create new genre for
        # it
        if genre_id == 'other':
            name = request.form['other']
            genre = getGenreByName(name)
            genre_id = genre.id
        movie.genre_id = genre_id
        return redirect(url_for('showMovie', movie_id=movie.id))

    return render_template('editMovie.html', movie=movie, genres=genres)


@app.route('/catalog/movies/<int:movie_id>/delete', methods=['POST', 'GET'])
def deleteMovie(movie_id):
    movie = session.query(Movie).filter_by(id=movie_id).one()
    user = session.query(User).filter_by(id=movie.user_id).one()

    if 'username' not in login_session or login_session[
            'user_id'] != movie.user_id:
        flash('Only %s can delete this movie' % user.name)
        return redirect(url_for('showCatalog'))

    if request.method == 'POST':
        reviews = session.query(Review).filter_by(movie_id=movie_id).all()
        for review in reviews:
            session.delete(review)
            session.commit()
        session.delete(movie)
        session.commit()
        flash('%s movie has been deleted' % movie.title)
        return redirect(url_for('showCatalog'))
    else:
        return render_template('deleteMovie.html', movie=movie)


# searchs TheOpenMovieDB
@app.route('/catalog/search', methods=['GET', 'POST'])
def search():
    if 'username' not in login_session:
        flash('You must login in order to add a movie')
        return redirect(url_for('showLogin'))
    if request.method == 'POST':
        query = request.form['query']
        api_key = json.loads(
            open(
                'tmdb_client_secrets.json',
                'r').read())['web']['api_key']
        url = "http://api.themoviedb.org/3/search/movie?api_key=%s&query=%s" % (
            api_key, query)
        r = requests.get(url)
        if r.status_code == 200:
            results = r.json()['results']
            if results:
                for result in results:
                    result['poster'] = result['poster_path']
                    result['description'] = result['overview']
                    result['year'] = result['release_date'].split('-')[0]

        return render_template('searchResults.html', results=results)
    else:
        return render_template('search.html')


# add movies from TheOpenMovieDB
@app.route('/catalog/search/addmovies', methods=["POST"])
def addMovies():
    num = 0
    if 'username' in login_session:
        user_id = login_session['user_id']
        results = request.form
        api_key = json.loads(
            open(
                'tmdb_client_secrets.json',
                'r').read())['web']['api_key']
        for key in results:

            try:
                movie = session.query(Movie).filter_by(tmdb_id=key).one()
                flash('%s is already in your catalog' % movie.title)

            except:
                url = "https://api.themoviedb.org/3/movie/%s?api_key=%s&append_to_response=trailers,credits" % (
                    key, api_key)
                print url
                r = requests.get(url)
                if r.status_code == 200:
                    data = r.json()
                    tmdb_id = data['id']
                    title = data['title']
                    description = data['overview']
                    poster = data['poster_path']
                    genre = data['genres'][0]["name"].lower()
                    genre_id = getGenreByName(genre).id
                    backdrop = "https://image.tmdb.org/t/p/original%s" % data[
                        'backdrop_path']
                    trailer = data['trailers']['youtube']
                    if len(trailer) > 0:
                        trailer = "https://www.youtube.com/embed/%s" % trailer[
                            0]['source']
                    else:
                        trailer = ""
                    actors = data['credits']['cast']
                    actor_list = []
                    for i in xrange(0, min(len(actors), 3)):
                        actor_list.append(actors[i]['name'])
                    actor_list = ", ".join(actor_list)
                    year = data['release_date'].split('-')[0]
                    movie = createMovie(
                        user_id,
                        genre_id,
                        title,
                        description,
                        year,
                        poster,
                        backdrop,
                        actor_list,
                        trailer,
                        tmdb_id)
                    num += 1
    if num > 0:
        flash('%s added to your catalog' % num)
    return redirect(url_for('showCatalog'))


@app.route('/catalog/movies/<int:movie_id>/review', methods=['POST'])
def addReview(movie_id):
    user_id = request.form['user_id']
    if session.query(Review).filter_by(
            movie_id=movie_id,
            user_id=user_id).count() > 0:
        flash("You have already reviewed this movie")
    else:
        comment = request.form['review']
        rating = request.form['score']
        review = Review(
            user_id=user_id,
            movie_id=movie_id,
            rating=rating,
            review=comment)
        session.add(review)
        session.commit()
        movie = updateRating(movie_id)
        session.add(movie)
        session.commit()
    return redirect(url_for('showMovie', movie_id=movie_id))


@app.route('/catalog/reviews/<int:review_id>/edit', methods=['POST', 'GET'])
def editReview(review_id):
    review = session.query(Review).filter_by(id=review_id).one()
    user = getUser(review.user_id)
    if login_session['user_id'] != review.user_id:
        flash('Only %s can edit this review' % user.name)
        return redirect(url_for('showMovie', movie_id=review.movie_id))

    movie = session.query(Movie).filter_by(id=review.movie_id).one()
    if request.method == "POST":
        review.rating = request.form['score']
        review.review = request.form['review']
        session.add(review)
        session.commit()
        movie = updateRating(review.movie_id)
        session.add(movie)
        session.commit()
        return redirect(url_for('showMovie', movie_id=movie.id))
    else:
        return render_template('editReview.html', review=review, movie=movie)


@app.route('/catalog/reviews/<int:review_id>/delete', methods=['POST', 'GET'])
def deleteReview(review_id):
    review = session.query(Review).filter_by(id=review_id).one()
    user = getUser(review.user_id)
    if login_session['user_id'] != review.user_id:
        flash('Only %s can edit this review' % user.name)
        return redirect(url_for('showMovie', movie_id=review.movie_id))
    if request.method == 'POST':
        session.delete(review)
        session.commit()
        movie = updateRating(review.movie_id)
        session.add(movie)
        session.commit()
        flash('Review has been deleted')
        return redirect(url_for('showMovie', movie_id=review.movie_id))
    else:
        movie = getMovie(review.movie_id)
        return render_template('deleteReview.html', movie=movie)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)

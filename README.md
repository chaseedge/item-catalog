# catalog
Udacity - item catalog app

# To Do List
- Implement other 3rd party authentications (e.g. Google, Twitter)
- Add pagination
- Add search for existing movie ratings
- Add sorting to Genre pages
- Modularize code

## Description
This app is allows users to build a catalog of genres and movies. Utilizing [The Movie DB's API](https://www.themoviedb.org/documentation/api), users can added their favorite movies. Users are also able to rate and review the movies in the catalog.
Only registered users can add or review movies.Only the user that originally added the movie can make changes to it. Users are also able to change or delete their reviews of a movie. 
A 3rd party authentication system (Facebook) is implemented to allow users to login. Also, a simple email login was added for testing purposes. 
This app also has JSON endpoints for movie details.
This app is based upon the Flask Python framework for the back end, and it leverages the Backbone JS framework for the front end. The UX should be fine on any device.


## Requirements
- [Vagrant](https://www.vagrantup.com/)
- [VirtualBox](https://www.virtualbox.org/)
- [Python ~2.7](https://www.python.org/)
- [facebook login app_id](https://developers.facebook.com)
- [The Movie DB api key](https://www.themoviedb.org/documentation/api)

## Set Up

For an initial set up please follow these 2 steps:

1. Download or clone the [fullstack-nanodegree-vm repository](https://github.com/udacity/fullstack-nanodegree-vm).

2. Find the *catalog* folder and replace it with the content of this current repository, by either downloading it or cloning it - [Github Link](https://github.com/chaseedge/Movie-Review-Catalog).

3. Place your facebook app_id and app_secret in a file called fb_client_secrets.json like this:
```
{
  "web": {
    "app_id": "",
    "app_secret": ""
  }
}
```
4. Place your TheMovieDB api key in a file called tmdb_client_secrets.json like this:
```
{
  "web": {
    "api_key": "",
    "access_token": ""
  }
}
```

## Usage
To run the app in your terminal: 
1. Navigate to the vagrant folder you cloned in Set Up Step 1.

2. From the *vagrant* folder, start your virtual machine:

`vagrant up`

`vagrant ssh`

3. Navigate to the catalog folder:

`cd /vagrant/catalog`

4. Build the database:

`python db_setup.py`

5. Launch the app:

`python main.py`

After the last command you are able to browse the application at this URL:

`http://localhost:5000/`

It is important you use *localhost* instead of *0.0.0.0* inside the URL address. That will prevent OAuth from failing.



## Credits
Star ratings are use [Raty](https://github.com/wbotelhos/raty)
Movie info is from [The Movie DB](https://www.themoviedb.org)
This app is not intended for commercial use. It's just for educational purpose.

# HOSTEL

Hostel is a Network company's internal management system. Features included:

* Customers, partners, phones and employees database 
* Resource management (IPAM, VLANS, Equipment)
* Customer services
* Datacenters and racks space management
* APIs for external apps
* Configuring monitoring
* Documents (agreements, invoices, etc)
* Dynamically building network maps

Made with Python and Django. MySQL as a DB

## Getting Started

These instructions will get you a copy of the project up and running 
on your local machine for development and testing purposes.

### Create a virtual env

```
mkdir -p venv/hostel
virtualenv --python=python3 venv/hostel
source venv/hostel/bin/activate
```

### Get the source code

```
mkdir hostel
git clone <this repo URL> hostel
```

### Installing the requirements

```
pip install -r hostel/requirements.txt
```

### Edit the configuration file

```
cp hostel/settings_example.py hostel/settings.py
vi hostel/settings.py
```

### Creating database and a DB user

We assuming that you have MySQL already installed in your system. Don't use the password from the example.
```
$ mysql
mysql> CREATE DATABASE hostel;
mysql> CREATE USER 'hostel_user'@'localhost' IDENTIFIED BY 'Phei9uec';
mysql> GRANT ALL PRIVILEGES ON hostel.* TO 'hostel_user'@'localhost';
mysql> FLUSH PRIVILEGES;
```

### Editing the settings file

Open hostel/settings.py and make following steps:

* Define SECRET_KEY. It is recommended to be >= 50 characters long.
* Define DATABASE settings
* Run command that creates DB tables
```
$ python manage.py migrate
```

### Creating a superuser
```
$ python manage.py createsuperuser

Username: admin
Email: admin@company.org
Password: 
Password (again): 
Superuser created successfully.
```

### Run Hostel on the Localhost

```
$ python manage.ry runserver

Performing system checks...

System check identified no issues (0 silenced).
October 18, 2020 - 01:57:40
Django version 2.1.5, using settings 'hostel.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

Now you can open http://127.0.0.1:8000 with your browser 
and log in to the Hostel with credentials you just created.

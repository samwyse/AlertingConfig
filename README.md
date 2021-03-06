# AlertingConfig
## Synopsis
This application produces a report describing the alerting configuration
of a ViPR SRM installation.  While SRM has a GUI allowing easy
configuration of the alerting module, there does not appear to be any way
to view the configuration in its entirety for project documentation, or
to preserve a human-readable description to track changes.

## Usage
To use this application, you first need an XML file. There are two ways to
get one using the ViPR SRM GUI.

The first is from the alerting frontend GUI. This allows you to download
(and thus report on) a subset of the total configuration, but does not 
provide access to the entire configuration.

![Image of Alerting Frontend](https://raw.githubusercontent.com/samwyse/AlertingConfig/master/src/static/AlertingFrontend.png)

The other is by accessing the alerting backend from the centralized 
management GUI. This allows you to report on the entire alerting 
configuration in a single document. 

![Image of Centralized Management](https://raw.githubusercontent.com/samwyse/AlertingConfig/master/src/static/CentralizedManagement.png)

(My free AWS instance has expired, so the web interface is no longer around.)

Once the desired XML file has been obtained, navigate to the web interface
to upload it to the report generator. There are two options provided. 
One allows you to choose whether to report on all alert definitions, 
or only those that are enabled (the default). The other is an experimental 
feature to in-line the HTML style sheets instead of using external CSS 
files.

Please note that the report can take several minutes to generate. Once 
produced, the report can be saved from your web browser. 

## Installation

If you are starting from, for example, a fresh EC2 instance, you must 
prepare your installation.

```sh
sudo yum install git docker
sudo /etc/rc.d/init.d/docker start
```

This application can be deployed directly from GitHub to a Docker container.

```sh
git clone https://github.com/samwyse/AlertingConfig.git
cd AlertingConfig
sudo make
sudo make run
```

Once installed, update it periodically.

```sh
cd AlertingConfig
git pull
sudo make
sudo make run
```

If you make local changes, push them upstream.

```sh
cd AlertingConfig
git status
git commit -a
git push
```

## Issues

See <https://github.com/samwyse/AlertingConfig/issues>


# Use the official Apache image as a base image
FROM httpd:2.4

# Install mod_wsgi for Apache
RUN apt-get update \
    && apt-get install -y libapache2-mod-wsgi-py3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /var/www/html

# Copy the Flask application files into the container
COPY ./docs /var/www/html

# Enable mod_wsgi
RUN sed -i '/^#.*mod_wsgi.so/s/^#//' /usr/local/apache2/conf/httpd.conf

# Configure Apache to serve the Flask application
COPY apache-flask.conf /usr/local/apache2/conf/extra/httpd-flask.conf

# Expose port 80
EXPOSE 80

# Start Apache in the foreground
CMD ["apachectl", "-D", "FOREGROUND"]

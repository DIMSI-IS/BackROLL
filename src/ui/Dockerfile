FROM httpd:2.4
COPY ./dist/ /usr/local/apache2/htdocs/


COPY create_config_js.sh .
RUN chmod +x create_config_js.sh
COPY docker_entrypoint.sh .
RUN chmod +x docker_entrypoint.sh

EXPOSE 80
CMD ["/bin/sh", "docker_entrypoint.sh"]
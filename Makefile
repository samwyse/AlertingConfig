build:
	docker build --tag=alerting-reports .

run:
	(docker kill webserver; docker rm webserver; true) >/dev/null 2>&1
	docker run -d -p 80:80 --name=webserver alerting-reports
	sleep 3; docker ps -a

sh:
	docker exec -i -t webserver /bin/sh

clean:
	docker ps -a | awk 'NR>1{print $$NF}' | xargs docker rm; true

cleanest:
	docker images | awk 'NR>1{print $$3}' | xargs docker rmi; true

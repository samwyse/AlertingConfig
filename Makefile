build:
	docker build --tag=alerting-reports .

run:
	(docker kill worker.1; docker rm worker.1; true) >/dev/null 2>&1
	docker run -d -p 80:80 --name=worker.1 alerting-reports
	sleep 3; docker ps -a

sh:
	docker exec -i -t worker.1 /bin/sh

clean:
	docker ps -a | awk 'NR>1{print $$NF}' | xargs docker rm; true

cleanest:
	docker images | awk 'NR>1{print $$3}' | xargs docker rmi; true

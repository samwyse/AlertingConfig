build:
	docker build --tag=alerting-reports .

run:
	$(MAKE) kill
	$(MAKE) clean
	docker run -d -p 80:80 --name=webserver alerting-reports
	sleep 3; docker ps -a

sh:
	docker exec -i -t webserver /bin/sh

kill:
	docker ps -a | awk 'NR>1{print $$NF}' | xargs docker kill; true

clean:
	docker ps -a | awk 'NR>1{print $$NF}' | xargs docker rm; true

cleanest:
	docker images | awk 'NR>1{print $$3}' | xargs docker rmi; true

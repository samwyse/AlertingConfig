default: alpine

alpine:
	docker build --tag=alerting-reports --file=Dockerfile.alpine .
	$(MAKE) restart-workers

ubuntu:
	docker build --tag=alerting-reports --file=Dockerfile.ubuntu .
	$(MAKE) restart-workers

pyrun:
	docker build --tag=alerting-reports --file=Dockerfile.pyrun .
	$(MAKE) restart-workers

sh:
	docker exec -i -t worker.1 /bin/sh

restart-workers:
	(docker kill worker.1; docker rm worker.1; true) >/dev/null 2>&1
	docker run -d -p 80:80 --name=worker.1 alerting-reports
	sleep 3; docker ps -a

clean:
	docker ps -a | awk 'NR>1{print $$NF}' | xargs docker rm; true

cleanest:
	docker images | awk 'NR>1{print $$3}' | xargs docker rmi; true

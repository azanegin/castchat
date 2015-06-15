CastChat - simple tool for managing your worker group

Usage
1) start servers on your workers adding paramter --server:
python devopsscript.py --server

This will invoker starting servers and making them to listen to port due to get group messages.

2) If you want your workers to execute some file just type:

python devopsscript.py --client --filename local_file

This will invoke upload-execution-statistic_collection loop:
	firsly local_file would be uploaded on all of your worker using multicast
	secondly each of workers would execute uploaded file
	thirdly execution statistics would be sent to client 

3) If you want to specify port of woker or server just set --port parameter, for example:
python devopsscript --server --port port_number

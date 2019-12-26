vessel1='10.1.0.1'
vessel2='10.1.0.2'
vessel3='10.1.0.3'
vessel4='10.1.0.4'

for i in $(seq 0 5); do
    curl -d 'entry=msg '${i}' from '${vessel1}'' 'POST' 'http://'${vessel1}':80/board' >/dev/null &
    curl -d 'entry=modified&delete=0' 'POST' 'http://'${vessel2}':80/board/('$((${i} + 1))',"'${vessel2}'")/' >/dev/null &
    curl -d 'entry=msg '${i}' from '${vessel2}'' 'POST' 'http://'${vessel3}':80/board' >/dev/null &
    curl -d 'entry=None&delete=1' 'POST' 'http://'${vessel2}':80/board/('${i}',"'${vessel4}'")/' >/dev/null &
done

# curl -d 'entry=modified&delete=0' 'POST' 'http://'${vessel1}':80/board/(-1,"'${vessel1}'")/' >/dev/null
# sleep 5
# curl -d 'entry=msg '1' from '${vessel1}'' 'POST' 'http://'${vessel1}':80/board' >/dev/null

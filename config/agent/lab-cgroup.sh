#!/bin/sh
# ----------------------------------------------------------------------------
#  Metricas por contenedor desde el cgroup v2.
#  Motivo: dentro de un contenedor /proc/stat y /proc/meminfo muestran los datos
#  del kernel compartido (toda la VM de Docker), asi que los items estandar de
#  "Linux by Zabbix agent" no distinguen un contenedor de otro. El cgroup si.
# ----------------------------------------------------------------------------
CG=/sys/fs/cgroup

case "$1" in
  cpu_pct)
    read -r quota period < "$CG/cpu.max"
    a=$(awk '$1=="usage_usec"{print $2}' "$CG/cpu.stat")
    sleep 1
    b=$(awk '$1=="usage_usec"{print $2}' "$CG/cpu.stat")
    cores=$(awk -v q="$quota" -v p="$period" -v n="$(nproc)" 'BEGIN{ if (q=="max") print n; else printf "%.4f", q/p }')
    awk -v a="$a" -v b="$b" -v c="$cores" 'BEGIN{ v=(b-a)/(1000000*c)*100; if (v<0) v=0; printf "%.2f", v }'
    ;;
  mem_used)
    cur=$(cat "$CG/memory.current")
    ina=$(awk '$1=="inactive_file"{print $2}' "$CG/memory.stat")
    echo $((cur - ${ina:-0}))
    ;;
  mem_limit)
    m=$(cat "$CG/memory.max")
    if [ "$m" = "max" ]; then m=$(awk '/MemTotal/{print $2*1024}' /proc/meminfo); fi
    echo "$m"
    ;;
  mem_pct)
    cur=$(cat "$CG/memory.current")
    ina=$(awk '$1=="inactive_file"{print $2}' "$CG/memory.stat")
    m=$(cat "$CG/memory.max")
    if [ "$m" = "max" ]; then m=$(awk '/MemTotal/{print $2*1024}' /proc/meminfo); fi
    awk -v c="$cur" -v i="${ina:-0}" -v m="$m" 'BEGIN{ printf "%.2f", (c-i)*100/m }'
    ;;
  pids)
    cat "$CG/pids.current"
    ;;
  *)
    echo "ZBX_NOTSUPPORTED"
    exit 1
    ;;
esac

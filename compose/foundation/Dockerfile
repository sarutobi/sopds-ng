# Docker file to build foundation styles

FROM node:24-trixie-slim AS build

ARG user_id=1000
ARG group_id=1000
ARG project_name="foundation"

# install foundation packages
RUN apt update && apt install ca-certificates git --no-install-recommends --assume-yes

# Создаём группу и пользователя с нужными ID.
# Если значение ID больше нуля (исключаем "root" ID) и в системе уже есть пользователь или группа с указанным ID,
# пересоздаём пользователя или группу с именем "app".
RUN <<EOF
[ $user_id -gt 0 ] && user="$(id --name --user $user_id 2> /dev/null)" && userdel "$user"

if [ $group_id -gt 0 ]; then
  group="$(id --name --group $group_id 2> /dev/null)" && groupdel "$group"
  groupadd --gid $group_id $project_name
fi

[ $user_id -gt 0 ] && useradd --uid $user_id --gid $group_id --home-dir "/$project_name" $project_name

EOF

WORKDIR /foundation
USER foundation

RUN git clone https://github.com/foundation/foundation-zurb-template .
RUN yarn


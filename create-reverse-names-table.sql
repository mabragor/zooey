use zooey;
create table if not exists reverse_names (
  id bigint(64) unsigned,
  path varchar(1000) character set utf8,
  primary key (id)
);

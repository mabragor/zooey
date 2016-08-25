use zooey;
create table if not exists positions (
  parent_id bigint(64) unsigned,
  child_id bigint(64) unsigned,
  x bigint(64),
  y bigint(64),
  w bigint(64),
  h bigint(64),
  primary key (parent_id)
);

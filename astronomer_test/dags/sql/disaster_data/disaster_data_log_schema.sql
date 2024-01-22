create table if not exists disaster_data_log (
    __filename varchar(200),
    date_loaded timestamp default now()
)
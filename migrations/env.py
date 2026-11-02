import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# 既にあるロガー（ログインの記録 app.auth など）を止めない
# （同じプロセスの中でmigrationを動かしたあとも、ログを残すため。
# デモデータの作成・テスト）
fileConfig(config.config_file_name, disable_existing_loggers=False)
logger = logging.getLogger('alembic.env')


def get_engine():
    # Flask-SQLAlchemy 3以降の書き方。生成されたときの書き方
    # （get_engine()）は、3.1で非推奨になり、警告が出るため、使わない。
    return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


# 本番で通す操作（Alembic が env.py に渡す処理の名前）。ほかの操作は、
# 本番では断る（断る名前の一覧にすると、Alembic の更新で増えた操作を、
# 黙って通してしまうため）。
# - upgrade：flask db upgrade（DBを新しい形にする）
# - display_version：flask db current（今の版を表示する）
# - _display_current_history：flask db history -i（履歴を表示する）
# 断るもの（例）：downgrade（DBを古い形に戻し、列や表のデータが消える）、
# do_stamp（DBを変えずに「どこまで当てたか」の記録だけを書き換え、次の
# upgrade が、当てるべき migration を飛ばしうる）、retrieve_migrations
# （flask db migrate・check。本番で migration のファイルを作ると、レビューを
# 通らないまま、次の upgrade で当たりうる。migration は Mac で作る）
PRODUCTION_ALLOWED_OPERATIONS = {
    "upgrade",
    "display_version",
    "_display_current_history",
}


def refuse_destructive_operation_in_production():
    """本番（APP_ENV=production）で、上の一覧にない操作を断る。

    Flask-Migrate の db コマンドは、このアプリのコマンドと違い、中を
    変えられないため、ここ（すべての db コマンドが通る場所）で断る。
    どの操作かは、Alembic が渡す処理の名前で見分ける（公開の仕組みで
    ないため、Alembic の更新で変わりうる。名前が変わったら、通すはずの
    操作も断られるので、気づける。tests/test_production.py が、upgrade・
    current が通り、downgrade・stamp・migrate・check が断られることを
    確かめる）。
    """
    if not current_app.config.get("PRODUCTION"):
        return
    operation = context._proxy.context_opts.get("fn")
    name = getattr(operation, "__name__", None)
    if name not in PRODUCTION_ALLOWED_OPERATIONS:
        raise RuntimeError(
            "本番では、この操作（db downgrade・db stamp など）はできません。"
            "戻すときは、バックアップから戻します（docs/development/deploy.md）"
        )


refuse_destructive_operation_in_production()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

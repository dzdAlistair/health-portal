"""健康大数据门户平台 — Flask 入口"""
from flask import Flask
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 注册蓝图
    from blueprints.portal import portal_bp
    from blueprints.admin import admin_bp
    from blueprints.resource import resource_bp
    from blueprints.analysis import analysis_bp

    app.register_blueprint(portal_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(resource_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

module.exports = {
    apps: [
        {
            name: 'beeworklife',
            script: 'server.py',
            interpreter: 'python',
            instances: 1,
            max_memory_restart: '1G',
            env: {
                FLASK_APP: 'server.py',
                FLASK_ENV: 'production',
                FLASK_RUN_PORT: 60812,
                SECRET_KEY: 'my_secret_key',
            },
        },
    ],
};

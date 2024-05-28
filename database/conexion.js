// db.js
const sql = require('mssql');

const config = {
  user: 'sa',
  password: 'admin',
  server: 'SOUVENIR',
  database: 'UTP_Inventary',
  options: {
    encrypt: false,
    trustServerCertificate: true // Solo se necesita cuando se conecta a un servidor local
  }
};

const poolPromise = sql.connect(config)
  .then(pool => {
    console.log('Conectado a SQL Server');
    return pool;
  })
  .catch(err => {
    console.error('Error al conectar a SQL Server:', err);
    throw err;
  });

module.exports = {
  sql,
  poolPromise
};


const express = require("express");
const app = express();
const inventarioRoutes = require('./routes/inventarioRoutes');

const dbConfig = require('./database/conexion');

app.get("/", (req, res) => {
  res.send('Hola mundo');
});

app.use('/inventario', inventarioRoutes);

app.listen(6500, () => {
  console.log("Servidor activo");
});

const mssql = require('mssql');
const db = require('../database/conexion');

class InventarioController {
    constructor() { }
    consultar(req, res) {
        try {
            mssql.query(`SELECT * FROM Items`,
                (err, rows) => {
                    if (err) {
                        res.status(400).send(err);
                    }
                    res.status(200).json(rows);
                });
        } catch (err) {
            res.status(500).send(err.message);
        }

    }
    async consultarPorId(req, res) {
        const { id } = req.params;
        try {
            const pool = await mssql.connect(db);
            const result = await pool.request()
                .input('id', mssql.Int, id)
                .query('SELECT * FROM Items WHERE id = @id');

            res.status(200).json(result.recordset[0]);
        } catch (err) {
            res.status(500).send(err.message);
        }
    }
    async ingresar(req, res) {
        try {
            const { HOST, Tipo, Ambiente } = req.body;
            if (!HOST || !Tipo || !Ambiente) {
                return res.status(400).send('Todos los campos son requeridos');
            }

            await db.connect();
            const result = await db.request()
                .input('HOST', mssql.NVarChar, HOST)
                .input('Tipo', mssql.NVarChar, Tipo)
                .input('Ambiente', mssql.NVarChar, Ambiente)
                .query(`INSERT INTO Items (HOST, Tipo, Ambiente) VALUES (@HOST, @Tipo, @Ambiente); SELECT SCOPE_IDENTITY() AS id;`);

            res.status(201).json({ id: result.recordset[0].id });
        } catch (err) {
            res.status(500).send(err.message);
        }
    }
    actualizar(req, res) {
        res.json({
            message: 'Actualizacion de item'
        })
    }
    borrar(req, res) {
        res.json({
            message: 'Eliminacion de item'
        })
    }
}

module.exports = new InventarioController();
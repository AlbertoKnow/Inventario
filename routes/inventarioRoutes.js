const express = require('express');
const router = express.Router();
const inventarioController = require('../controllers/inventarioController')

router.get('/', inventarioController.consultar);

router.post('/', inventarioController.ingresar);

router.route('/:id')
    .get(inventarioController.consultarPorId)
    .put(inventarioController.actualizar)
    .delete(inventarioController.borrar)

module.exports = router;
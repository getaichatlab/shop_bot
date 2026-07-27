"""Background services and external integrations.

Nothing is re-exported here on purpose: binding the name `rates` at package
level would shadow the `services.rates` submodule, so `import services.rates`
would hand back the RateProvider instance instead of the module.
Import from the submodule directly: `from services.rates import rates`.
"""

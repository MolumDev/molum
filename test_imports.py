import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestImports")

try:
    import config
    logger.info("Successfully imported config.")
    
    import database
    logger.info("Successfully imported database.")
    
    import keyboards
    logger.info("Successfully imported keyboards.")
    
    import middlewares.i18n
    logger.info("Successfully imported middlewares.i18n.")
    
    import middlewares.throttling
    logger.info("Successfully imported middlewares.throttling.")
    
    import handlers.admin
    import handlers.start
    import handlers.profile
    import handlers.tasks
    import handlers.token
    import handlers.language
    import handlers.webapp
    logger.info("Successfully imported all handlers.")
    
    import bot
    logger.info("Successfully imported bot main script.")
    
    print("ALL MODULES IMPORTED SUCCESSFULLY! NO SYNTAX OR CONFIG ERRORS ENCOUNTERED.")
    sys.exit(0)
except Exception as e:
    logger.critical(f"Import test failed: {e}", exc_info=True)
    sys.exit(1)

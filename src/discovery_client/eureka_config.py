from py_eureka_client import eureka_client


async def register_with_eureka():
    """
    Registers the application with the Eureka server.

    :param app_name: Name of the application to register.
    :param instance_port: Port on which the application is running.
    :param eureka_server: URL of the Eureka server.
    """
    await eureka_client.init_async(
        eureka_server="http://localhost:8761/eureka/",
        app_name="inventory-service",
        instance_port=8089,
        instance_host="localhost",
        health_check_url="http://localhost:8089/health",
        status_page_url="http://localhost:8089/info",
        data_center_name="MyOwn",
    )

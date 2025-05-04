from views import set_page_navigation
from classes.config import set_page_config, initialize_session

def main():
    initialize_session()
    set_page_config()
    set_page_navigation()

if __name__ == '__main__':
    main()

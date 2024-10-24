#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <time.h>
#include <stdlib.h>

#define CACHE_SIZE 20

struct Cache
{
    int id;
    bool set;
    time_t timestamp;
};

struct ClientSubscription
{
    int changedId;
    time_t changedTime;
    int socketId;
};

// tabulka, s tim ktere ID bylo zneplatneno

int main(int argc, char *argv[])
{
    Cache cache[CACHE_SIZE];
    time_t currentTime = time(NULL);

    for(int i = 0;i < CACHE_SIZE; i++)
    {
        cache[i].id = i;
        cache[i].set = true;
        cache[i].timestamp = currentTime;
    }

    //vytvoření socketu
    int sock_listen = socket( AF_INET, SOCK_STREAM, 0 );

    //vytvoření a naplnění struktury
    in_addr addr_any = { INADDR_ANY };
    sockaddr_in srv_addr;
    srv_addr.sin_family = AF_INET;
    srv_addr.sin_port = htons( 4444 );
    srv_addr.sin_addr = addr_any;

    int opt = 1;
    //nastavíme případné vlastnosti socketu
    setsockopt( sock_listen, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof( opt ) );
    //svážeme strukturu se socketem
    bind( sock_listen, (const sockaddr * ) &srv_addr, sizeof( srv_addr ) );
    //začneme naslouchat na daném portu
    listen( sock_listen, 1 );


    //proměnná pro vlastnosti příchozích socketů
    sockaddr_in rsa;
    int rsa_size = sizeof( rsa );                       


    //accept je blokující funkce, zde se program zastaví a rozběhne se až po navázání spojení
    //po navázání spojení se vytvoří nový socket na kterém se již komunikuje s klientem
    int sock_client = accept( sock_listen, ( sockaddr * ) &rsa, ( socklen_t * ) &rsa_size );

    printf("Připojil se někdo:\n");

    char data[1024];

    int r = read(sock_client,data,sizeof(data));

    printf("%s\n",data);

}

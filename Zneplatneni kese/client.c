#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <time.h>
#include <stdlib.h>

#define CACHE_SIZE 20

int main(void)
{
    int cache[CACHE_SIZE];

    char host[]="localhost";
    int port = 4444;


    // vytvoření socketu
    int sock_server = socket( AF_INET, SOCK_STREAM, 0 );

    // překlad doménových jmen na IP adresu
    hostent *hostip = gethostbyname( host );

    //struktura s vlastnostmi socketu
    sockaddr_in cl_addr;
    cl_addr.sin_family = AF_INET;
    cl_addr.sin_port = htons( port );
    cl_addr.sin_addr = * (in_addr * ) hostip->h_addr_list[ 0 ];

    //navázání spojení se servererm
    connect( sock_server, ( sockaddr * ) &cl_addr, sizeof( cl_addr ) );

    char data[] = "Ahoj";
    write(sock_server,data,sizeof(data));

    close(sock_server);

}

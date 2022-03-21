from iqoptionapi.stable_api import IQ_Option
import sys
from datetime import datetime, timedelta
from colorama import init, Fore, Back
from time import time

init(autoreset=True)

API = IQ_Option('email@email.com', 'Senha')
API.connect()

if API.check_connect():
    print('Conectado com sucesso!')
else:
    print('Erro ao conectar')
    input('\n\n Aperte enter para sair')
    sys.exit()
    
def cataloga(par, dias, prct_call, prct_put, timeframe = 60):
    data = []
    datas_testadas = []
    sair = False
    time_ = time()
    
    while sair == False:
        velas = API.get_candles(par, (timeframe * 60), 1000, time_)
        velas.reverse()
        
        for x in velas:
            if datetime.fromtimestamp(x['from']).strftime('&Y-%m-%d') not in datas_testadas:
                datas_testadas.append(datetime.fromtimestamp(x['from']).strftime('&Y-%m-%d'))
                
            if len(datas_testadas) <= dias:
                x.update({ 'cor': 'verde' if x['open'] < x['close'] else 'vermelha' if x['open'] > x['close'] else 'doji'})
                data.append(x)
                
            else:
                sair = True
                break
                
        time_ = int(velas[-1]['from'] - 1)
        
    analise = {}
    for velas in data:
        horario = datetime.fromtimestamp(velas['from']).strftime('%H:%M')
        
        if horario not in analise: analise.update({ horario: {'verde': 0, 'vermelha': 0, 'doji': 0, '%': 0, 'dir': ''} })
        analise[horario][velas['cor']] += 1
        
        try:
            analise[horario]['%'] = round(100 * (analise[horario]['verde'] / (analise[horario]['verde'] + analise[horario]['vermelha'] + analise[horario]['doji'])))
        except:
            pass
            
            
    for horario in analise:
        if analise[horario]['%'] > 50: analise[horario]['dir'] = 'CALL'
        if analise[horario]['%'] < 50: analise[horario]['dir'], analise[horario]['%'] = 'PUT ', (100 - analise[horario]['%'])
        
    return analise
    

print('\n\nQual timeframe deseja catalogar? ', end='')
timeframe = int(input())

print('\nQuantos dias para analisar? ', end='')
dias = int(input())

print('\nQual a porcentagem minima? ', end='')
porcentagem = int(input())

print('\nTestar com quantos martingales? ', end='')
martingale = input()

prct_call = abs(porcentagem)
prct_put = abs(100 - porcentagem)

P = API.get_all_open_time()

print('\n\n')

catalogacao = {}
for par in P['turbo']:
    if P['turbo'][par]['open'] == True:
        timer = int(time())
        
        print(Fore.GREEN + '*' + Fore.RESET + ' CATALOGANDO ' + par + '.. ', end='')
        
        catalogacao.update({par: cataloga(par, dias, prct_call, prct_put, timeframe)})
        
        if martingale.strip() != '':
            for horario in sorted(catalogacao[par]):
                mg_time = horario
                
                soma = {'verde': catalogacao[par][horario]['verde'], 'vermelha': catalogacao[par][horario]['vermelha'], 'doji': catalogacao[par][horario]['doji']}
                
                for i in range(int(martingale)):
                    i += 1
                    catalogacao[par][horario].update({'mg'+str(i): {'verde': 0, 'vermelha': 0, 'doji': 0, '%': 0}})
                    
                    mg_time = str(datetime.strptime((datetime.now()).strftime('%Y-%m-%d ') + mg_time, '%Y-%m-%d %H:%M') + timedelta(minutes=timeframe))[11:-3]
                    
                    if mg_time in catalogacao[par]:
                        catalogacao[par][horario]['mg' + str(i)]['verde'] += catalogacao[par][mg_time]['verde'] + soma['verde']
                        catalogacao[par][horario]['mg' + str(i)]['vermelha'] += catalogacao[par][mg_time]['verde'] + soma['vermelha']
                        catalogacao[par][horario]['mg' + str(i)]['doji'] += catalogacao[par][mg_time]['verde'] + soma['doji']
                        
                        catalogacao[par][horario]['mg' + str(i)]['%'] = round(100 * (catalogacao[par][horario]['mg' + str(i)]['verde' if catalogacao[par][horario]['dir'] == 'CALL' else 'vermelha'] / ( catalogacao[par][horario]['mg' + str(i)]['verde'] + catalogacao[par][horario]['mg' + str(i)]['vermelha'] + catalogacao[par][horario]['mg' + str(i)]['doji'] )))
                        
                        soma['verde'] += catalogacao[par][mg_time]['verde']
                        soma['vermelha'] += catalogacao[par][mg_time]['vermelha']
                        soma['doji'] += catalogacao[par][mg_time]['doji']
                        
                    else:
                        catalogacao[par][horario]['mg' + str(i)]['%'] = 'N/A'
        
        print('Finalizado em ' + str(int(time()) - timer) + ' segundos')
    
print('\n\n')

for par in catalogacao:
    for horario in sorted(catalogacao[par]):
        ok = False
        msg = ''
        
        if catalogacao[par][horario]['%'] >= porcentagem:
            ok = True
        else:
            if martingale.strip() != '':
                for i in range(int(martingale)):
                    if catalogacao[par][horario]['mg' + str(i + 1)]['%'] >= porcentagem:
                        ok = True
                        break
                        
    if ok == True:
        msg = Fore.YELLOW + par + Fore.RESET + ' - ' + horario + ' - ' + (Fore.GREEN if catalogacao[par][horario]['dir'] == 'CALL' else Fore.RED) + ' - ' + catalogacao[par][horario]['dir'] + Fore.RESET + ' - ' + str(catalogacao[par][horario]['%']) + '% - ' + Back.GREEN + Fore.BLACK + str(catalogacao[par][horario]['verde']) + Back.RED + str(catalogacao[par][horario]['vermelha']) + Back.RESET + Fore.RESET + str(catalogacao[par][horario]['doji'])
        
        if martingale.strip() != '':
            for i in range(int(martingale)):
                i += 1
                if str(catalogacao[par][horario]['mg' + str(i)]['%']) != 'N/A':
                    msg += ' | MG ' + str(i) + ' - ' + str(catalogacao[par][horario]['mg' + str(i)]['%']) + '% - ' + Back.GREEN + Fore.BLACK + str(catalogacao[par][horario]['mg' + str(i)]['verde']) + Back.RED + str(catalogacao[par][horario]['mg' + str(i)]['vermelha']) + Back.RESET + Fore.RESET + str(catalogacao[par][horario]['mg' + str(i)]['doji'])
                else:
                    msg += ' | MG ' + str(i) + ' - N/A - N/A'
                    
            print(msg)
            open('sinais_' + (datetime.now()).strftime('%Y-%m-%d') + '_' + str(timeframe) + 'M.txt', 'a').write(horario + ',' + par + ',' + catalogacao[par][horario]['dir'].strip() + '\n') #18:00,EURUSD,CALL
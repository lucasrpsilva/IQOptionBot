from iqoptionapi.stable_api import IQ_Option
import json
import time #para Suporte e Resistência
from datetime import datetime
from dateutil import tz
import sys
import numpy as np
from talib.abstract import *

API = IQ_Option('email@email.com', 'Senha')
API.connect()
API.change_balance('PRACTICE') # PRACTICE / REAL

while True:
    if API.check_connect() == False:
        print('Erro ao se conectar')
        API.reconnect()
    else:
        print('Conectado com sucesso')
        break
    
    time.sleep(1)

#Busca as informações do perfil 
def perfil():
    perfil = json.loads(json.dumps(API.get_profile_ansyc()))
    
    return perfil

#Converte timestamp para um Ano, Mês, Dia, Hora, Minuto e Segundo; na zona de horário GMT de São Paulo
def timestamp_converter(x):
    hora = datetime.strptime(datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
    hora = hora.replace(tzinfo=tz.gettz('GMT'))
    
    return str(hora.astimezone(tz.gettz('America/Sao Paulo')))[:-6]

#Retorna o valor da banca
def banca():
    return 'Dinheiro: ' + API.get_balance()

#Retorna o payout do par binário em 1 minuto
def payout(par):
    a = API.get_all_profit()
    return int(100 * a[par]['turbo'])

#Busca as velas de um par em tempo real
def candle_stream(par):
    API.start_candles_stream(par, 60, 1)
    time.sleep(1)

    vela = API.get_realtime_candles(par, 60)
    while True:
        for velas in vela:
            print(vela[velas]['close'])
        time.sleep(1)
    API.stop_candles_stream(par, 60)

#Busca as paridades abertas e as exibe com payout
def paridades_abertas_payout():
    par = API.get_all_open_time()

    for paridade in par['turbo']:
        if par['turbo'][paridade]['open'] == True:
            print('[ TURBO ]: ' + paridade + ' | Payout: ' + str(payout(paridade)))

#Busca o histórico (padrão último 3 trades) das binárias
def historico():
    status, historico = API.get_position_history_v2('turbo-option', 3, 0, 0, 0)

    for x in historico['positions']:
        print('PAR: ' + API.opcode_to_name(x['raw_event']['active_id']) + ' / DIRECAO: ' + str(x['raw_event']['direction']) + ' / VALOR: ' + str(x['invest']))
        print('LUCRO: ' + str(x['close_profit'] if x['close_profit'] == 0 else round(x['close_profit']-x['invest'], 2)) + ' | INICIO OP: ' + str(timestamp_converter(x['open_time'] / 1000)) + ' / FIM OP: ' + str(timestamp_converter(x['close_time'] / 1000)))
        print('\n')

#Faz uma entrada no par binário escolhido        
def entrada(par, valor, direcao, time):
    print('\nComprando ' + str(valor) + ' em ' + par + ' para ' + direcao + ' com expiracao ' + str(time))
    status, id = API.buy(valor, par, direcao, time)
    if status:
        while True:
            resultado, lucro = (API.check_win_v4(id))
            
            if status:
                if lucro > 0:
                    #print('\nWIN - ' + str(round(lucro,2)))
                    return 'win', round(lucro, 2)
                else:
                    #print('\nLOSS')
                    return 'loss', 0
                break

#Vende uma operação em aberto
def venda(id):
    print('Vendendo binaria: ', end='')
    status = API.sell_option(id)
    if 'error' in status['msg'][str(id)]:
        print('Erro ao vender operacao')
    else:
        print('Operacao vendida com sucesso')

#Faz entrada com sorosgale    
def sorosgale(par):
    print('Iniciando Sorosgale\n')
    
    lucro_total = 0
    nivel = 1
    lucro = 0
    mao = 1
    take = 4
    lucro_total_true = 0
    win_cont = 0
    loss_cont = 0
    
    print('\nTake: ' + str(take) + ' - Entrada inicial: ' + str((take/2)))
    
    while True:
        
        resultado, lucro = entrada(par, (take/2)+lucro, berman_tendencia(par), 5) #Trocar aqui o par e direção
        
        if resultado == 'win':
            lucro_total += lucro
            lucro_total_true += lucro
            mao += 1
            win_cont += 1
            print('\nNivel: ' + str(nivel) + ' - Mao: ' + str(mao) + ' | ' + str(resultado))
        else:
            lucro_total = 0
            lucro_total_true -= (take/2)+lucro
            mao = 1
            take += take/2
            print('\nNivel: ' + str(nivel) + ' - Mao: ' + str(mao) + ' | ' + str(resultado))
            nivel += 1
            loss_cont += 1
            
        if lucro_total >= take:
            print('WIN\n Nivel: ' + str(nivel) + ' - Mao: ' + str(mao) + ' | ' + str(take) + ' -> ' + str(lucro_total))
            print('\nTake atingido, reiniciando \n')
            lucro_total = 0
            nivel = 1
            lucro = 0
            mao = 1
            take = 4
        else:
            print(' Lucro: ' + str(lucro))
        
        print('\nWINs: ' + str(win_cont) + ' | LOSSes: ' + str(loss_cont))
        if win_cont + loss_cont >= 100:
            sys.exit()

        #stop(lucro_total_true, 25, -12.5)

#Verifica o stop
def stop(lucro, gain, loss):
    if lucro >= gain:
        print('\nProfit atingido, parando \n')
        sys.exit()
    if lucro <= loss:
        print('\nLoss atingido, parando \n')
        sys.exit()

#Pega a Tendência de um par
def tendencia(par, timeframe = 5):
    tendencia = "NONE"
    
    #while tendencia == "NONE": #Usar quando não estiver em conjunto com outro indicador
    print('\nAnalisando tendencia ')
    velas = API.get_candles(par, (int(timeframe)) * 60, 3, time.time())
        
    ultimo = round(velas[0]['close'], 4)
    primeiro = round(velas[-1]['close'], 4)
        
    diferenca = abs(round(((ultimo - primeiro)/primeiro)*100, 3))
    tendencia = "CALL" if ultimo < primeiro and diferenca > 0.01 else "PUT" if ultimo > primeiro and diferenca > 0.01 else "NONE"
    
    return tendencia

#Pega Suporte e Resistência de um par
def get_sr(par, timeframe = 1):
    print('\nBuscando suporte e resistencia')
    
    indicators = API.get_technical_indicators(par)
    
    sr={}
    for dados in indicators:
        if dados['candle_size'] == (int(timeframe) * 60) and 'Classic' in dados['name']:
            sr.update({dados['name'].replace('Classic ', ''): dados['value']})
            
    return sr

#Aplica a estratégia de Suporte e Resistência
def estrategia_suporte_resistencia(par):
    update = 0
    API.start_candles_stream(par, 60, 5)
    sr = get_sr(par, 5)

    while True:
        if update == 60 : sr = get_sr(par, 5)
                
        candles = API.get_realtime_candles(par, 60)
                
        for x in candles:
            print('\nAnalisando suporte e resistencia' + ' - R1: ' + str(sr['r1']) + ' - S1: ' + str(sr['s1']) + ' - Candle: ' + str(candles[x]['close']))
            if candles[x]['close'] <= sr['s1'] or candles[x]['close'] <= sr['s2'] or candles[x]['close'] <= sr['s3'] : entrada(par, 1000, 'CALL', 5)
            if candles[x]['close'] >= sr['r1'] or candles[x]['close'] >= sr['r2'] or candles[x]['close'] >= sr['r3'] : entrada(par, 1000, 'PUT', 5)
            break
            
        update += 1
        time.sleep(1)

#Aplica a estratégia de Suporte e Resistência com Tendência
def estrategia_suporte_resistencia_tendencia(par):
    update = 0
    API.start_candles_stream(par, 60, 1)
    sr = get_sr(par, 5)

    while True:
        if update == 60 : sr = get_sr(par, 1)
                
        candles = API.get_realtime_candles(par, 60)
                
        for x in candles:
            print('\nAnalisando suporte e resistencia' + ' - R1: ' + str(sr['r1']) + ' - S1: ' + str(sr['s1']) + ' - Candle: ' + str(candles[x]['close']))
            if (candles[x]['close'] <= sr['s1'] and tendencia(par) == "CALL") or (candles[x]['close'] <= sr['s2'] and tendencia(par) == "CALL") or (candles[x]['close'] <= sr['s3'] and tendencia(par) == "CALL") : return "CALL"
            if (candles[x]['close'] >= sr['r1'] and tendencia(par) == "PUT") or (candles[x]['close'] >= sr['r2'] and tendencia(par) == "PUT") or (candles[x]['close'] >= sr['r3'] and tendencia(par) == "PUT") : return "PUT"
            break
            
        update += 1
        time.sleep(1)
   
#Usa a estratégia de Bandas de Bollinger
def banda_bollinger(par, timeframe = 1):
    velas_q = 100

    while True:
        inicio = time.time()
        velas = API.get_candles(par, (int(timeframe)) * 60, velas_q, time.time())
        
        dados_f = {
                    'open': np.empty(velas_q),
                    'high': np.empty(velas_q),
                    'low': np.empty(velas_q),
                    'close': np.empty(velas_q),
                    'volume': np.empty(velas_q)
        }
        
        for x in range(0, velas_q):
            dados_f['open'][x] = velas[x]['open']
            dados_f['high'][x] = velas[x]['max']
            dados_f['low'][x] = velas[x]['min']
            dados_f['close'][x] = velas[x]['close']
            dados_f['volume'][x] = velas[x]['volume']
            
        up, mid, low = BBANDS(dados_f, timeperiod=14, nbdevup = 2.0, nbdevdn = 2.0, matype = 0)
        up = round(up[len(up)-2], 5)
        low = round(low[len(low)-2], 5)
        taxa_atual = round(velas[-1]['close'], 5)
        
        print('Taxa: ', taxa_atual,
              ' | Up: ', up,
              ' | Low: ', low,
              ' | Time: ', round(time.time() - inicio, 2), 'seg',
              ' | TVela: ', datetime.fromtimestamp(int(velas[-1]['at']) // 1000000000).strftime('%H:%M:%S')
        )
        
        if taxa_atual >= up or taxa_atual <= low:
            return 'PUT' if taxa_atual >= up else 'CALL'

#Usa a estratégia de Bandas de Bollinger com Tendência
def banda_bollinger_tendencia(par, timeframe = 1):
    velas_q = 100

    while True:
        inicio = time.time()
        velas = API.get_candles(par, (int(timeframe)) * 60, velas_q, time.time())
        
        dados_f = {
                    'open': np.empty(velas_q),
                    'high': np.empty(velas_q),
                    'low': np.empty(velas_q),
                    'close': np.empty(velas_q),
                    'volume': np.empty(velas_q)
        }
        
        for x in range(0, velas_q):
            dados_f['open'][x] = velas[x]['open']
            dados_f['high'][x] = velas[x]['max']
            dados_f['low'][x] = velas[x]['min']
            dados_f['close'][x] = velas[x]['close']
            dados_f['volume'][x] = velas[x]['volume']
            
        up, mid, low = BBANDS(dados_f, timeperiod=14, nbdevup = 2.0, nbdevdn = 2.0, matype = 0)
        up = round(up[len(up)-2], 5)
        low = round(low[len(low)-2], 5)
        taxa_atual = round(velas[-1]['close'], 5)
        
        print('Taxa: ', taxa_atual,
              ' | Up: ', up,
              ' | Low: ', low,
              ' | TVela: ', datetime.fromtimestamp(int(velas[-1]['at']) // 1000000000).strftime('%H:%M:%S')
        )
        
        if (taxa_atual >= up and tendencia(par) == "PUT") or (taxa_atual <= low and tendencia(par) == "CALL"):
            return 'PUT' if taxa_atual >= up else 'CALL'

#Usa a estratégia Berman
def berman(par, timeframe = 5):
    velas_q = 1000

    while True:
        inicio = time.time()
        velas = API.get_candles(par, (int(timeframe)) * 60, velas_q, time.time())
        
        dados_f = {
                    'open': np.empty(velas_q),
                    'high': np.empty(velas_q),
                    'low': np.empty(velas_q),
                    'close': np.empty(velas_q),
                    'volume': np.empty(velas_q)
        }
        
        for x in range(0, velas_q):
            dados_f['open'][x] = velas[x]['open']
            dados_f['high'][x] = velas[x]['max']
            dados_f['low'][x] = velas[x]['min']
            dados_f['close'][x] = velas[x]['close']
            dados_f['volume'][x] = velas[x]['volume']
        
        saida = EMA(dados_f, timeperiod=100)
        up, mid, low = BBANDS(dados_f, timeperiod=20, nbdevup = 2.5, nbdevdn = 2.5, matype = 0)
        
        up = round(up[len(up)-2], 5)
        low = round(low[len(low)-2], 5)
        taxa_atual = round(velas[-1]['close'], 5)
        emma = round(saida[-1], 5)
        
        print('Taxa: ', taxa_atual,
              ' | Up: ', up,
              ' | Low: ', low,
              ' | Time: ', round(time.time() - inicio, 2), 's',
              ' | TVela: ', datetime.fromtimestamp(int(velas[-1]['at']) // 1000000000).strftime('%H:%M:%S'),
              '\n EMA: ', emma, '| ESTA FORA!' if emma >up or emma < low else '| ESTA DENTRO!'
        )
        
        if (taxa_atual >= up and emma > up) or (taxa_atual <= low and emma < low):
            return 'PUT' if taxa_atual >= up else 'CALL'
            
#Usa a estratégia Berman + Tendência
def berman_tendencia(par, timeframe = 5):
    velas_q = 1000

    while True:
        inicio = time.time()
        velas = API.get_candles(par, (int(timeframe)) * 60, velas_q, time.time())
        
        dados_f = {
                    'open': np.empty(velas_q),
                    'high': np.empty(velas_q),
                    'low': np.empty(velas_q),
                    'close': np.empty(velas_q),
                    'volume': np.empty(velas_q)
        }
        
        for x in range(0, velas_q):
            dados_f['open'][x] = velas[x]['open']
            dados_f['high'][x] = velas[x]['max']
            dados_f['low'][x] = velas[x]['min']
            dados_f['close'][x] = velas[x]['close']
            dados_f['volume'][x] = velas[x]['volume']
        
        saida = EMA(dados_f, timeperiod=100)
        up, mid, low = BBANDS(dados_f, timeperiod=20, nbdevup = 2.5, nbdevdn = 2.5, matype = 0)
        
        up = round(up[len(up)-2], 5)
        low = round(low[len(low)-2], 5)
        taxa_atual = round(velas[-1]['close'], 5)
        emma = round(saida[-1], 5)
        
        print('Taxa: ', taxa_atual,
              ' | Up: ', up,
              ' | Low: ', low,
              ' | Time: ', round(time.time() - inicio, 2), 's',
              ' | TVela: ', datetime.fromtimestamp(int(velas[-1]['at']) // 1000000000).strftime('%H:%M:%S'),
              '\n EMA: ', emma, '| ESTA FORA!' if emma >up or emma < low else '| ESTA DENTRO!'
        )
        
        if (taxa_atual >= up and emma > up and tendencia(par) == 'PUT') or (taxa_atual <= low and emma < low and tendencia(par) == 'CALL'):
            return 'PUT' if taxa_atual >= up else 'CALL'

sorosgale('EURJPY-OTC')
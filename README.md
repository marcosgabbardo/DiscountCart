# Amazon Price Monitor

Monitor de precos de produtos da Amazon Brasil. Receba alertas no terminal quando os precos atingirem seu alvo.

## Funcionalidades

- **Adicionar Produtos**: Monitore qualquer produto da Amazon Brasil via URL
- **Definir Preco Alvo**: Defina o preco que deseja pagar
- **Historico de Precos**: Acompanhe as variacoes de preco ao longo do tempo
- **Alertas Inteligentes**: Seja notificado quando:
  - Preco atinge seu alvo
  - Preco cai abaixo da media de 7/30 dias
  - Novo preco minimo detectado
- **Estatisticas**: Visualize precos medios, minimos e maximos

## Requisitos

- Python 3.8+
- MySQL 5.7+ ou MariaDB 10.3+

## Instalacao

1. **Clone o repositorio**:
```bash
git clone https://github.com/yourusername/DiscountCart.git
cd DiscountCart
```

2. **Crie o ambiente virtual**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configure o ambiente**:
```bash
cp .env.example .env
# Edite o .env com suas credenciais do banco de dados
```

5. **Inicialize o banco de dados**:
```bash
python price_monitor.py init-db
```

## Configuracao

Edite o arquivo `.env` com suas configuracoes:

```env
# Configuracao do Banco de Dados
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=amazon_price_monitor

# Configuracao do Scraping
SCRAPE_DELAY_MIN=2
SCRAPE_DELAY_MAX=5

# Configuracao de Alertas
PRICE_DROP_THRESHOLD_PERCENT=10
```

## Uso

### Adicionar um Produto para Monitorar

```bash
python price_monitor.py add "https://www.amazon.com.br/dp/B0BTXDTD6H" "R$80,99"
```

Formatos de preco aceitos:
- `R$80,99`
- `80,99`
- `80.99`
- `R$ 1.234,56`

### Listar Todos os Produtos Monitorados

```bash
python price_monitor.py list
```

Saida:
```
Monitored Products (3)
--------------------------------------------------------------------------------
ID   Product                                   Current       Target        Difference   Status
1    Wild Side American Whiskey...             R$ 89,90      R$ 80,99      R$ 8,91
2    Echo Dot 5a Geracao...                    R$ 299,00     R$ 249,99     R$ 49,01
3    Kindle Paperwhite...                      R$ 499,00     R$ 499,00     R$ 0,00      OK
```

### Verificar Precos e Alertas

```bash
python price_monitor.py check
```

### Atualizar Todos os Precos

```bash
python price_monitor.py update
```

Busca os precos atuais na Amazon para todos os produtos monitorados.

### Ver Historico de Precos

```bash
python price_monitor.py history 1 --days 30
```

### Ver Detalhes do Produto

```bash
python price_monitor.py detail 1
```

### Ver Alertas Disparados

```bash
python price_monitor.py alerts
```

### Remover um Produto

```bash
python price_monitor.py remove 1
```

## Automacao

### Usando Cron (Linux/Mac)

Adicione ao crontab para verificar precos a cada hora:

```bash
crontab -e
```

Adicione:
```
0 * * * * cd /path/to/DiscountCart && /path/to/venv/bin/python price_monitor.py update >> /var/log/price_monitor.log 2>&1
```

### Usando Task Scheduler (Windows)

Crie uma tarefa agendada para executar:
```
python C:\path\to\DiscountCart\price_monitor.py update
```

## Schema do Banco de Dados

A aplicacao usa 3 tabelas principais:

- **products**: Produtos monitorados com URLs e precos alvo
- **price_history**: Registros historicos de precos
- **alerts**: Configuracoes e status dos alertas

## Limitacoes

- **Web Scraping**: Esta ferramenta usa web scraping que pode quebrar se a Amazon mudar a estrutura das paginas
- **Rate Limiting**: Delays embutidos para evitar bloqueio pela Amazon
- **Apenas Amazon Brasil**: Atualmente otimizado para amazon.com.br

## Melhorias Futuras

- [ ] Suporte para outras regioes da Amazon
- [ ] Automacao com navegador (Selenium) para scraping mais confiavel
- [ ] Predicao de precos baseada em dados historicos
- [ ] Interface web dashboard
- [ ] Comparacao de precos com outros e-commerces

## Licenca

MIT License - Veja o arquivo [LICENSE](LICENSE) para detalhes.

## Aviso

Esta ferramenta e apenas para uso pessoal. Respeite os termos de servico da Amazon e use com responsabilidade.

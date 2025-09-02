## FIAP - Faculdade de Informática e Administração Paulista

<p style="padding-top: 40px">
    <a href= "https://www.fiap.com.br/">
        <img src="../assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=30%>
    </a>
</p>

<br>

# Reply - Enterprise Challenge - SIMP - Sistema Inteligente de Manutenção Preditiva
### Sprint 3


## Grupo TiãoTech

## 👨‍🎓 Integrantes
- <a href="https://www.linkedin.com/in/edmilson-marciano-02648a33">RM565912 - Edmilson Marciano</a>
- <a href="https://www.linkedin.com/in/jayromazzi">RM565576 - Jayro Mazzi Junior</a>
- <a href="https://www.linkedin.com/in/lucas-a-5b7a70110">RM563353 - Lucas Arcanjo</a>
- <a href="https://www.linkedin.com/in/vinicius-andrade-01208822b">RM564544 - Marcus Vinicius de Andrades Silva Malaquias</a>

## 👩‍🏫 Professores
### Tutor(a) 
- <a href="https://www.linkedin.com/in/lucas-gomes-moreira-15a8452a">Lucas Gomes Moreira</a>
### Coordenador(a)
- <a href="https://www.linkedin.com/in/andregodoichiovato">Andre Godoi Chiovato</a>

---

## Conteúdo

.

## Descrição


## Objetivos desta entrega

* **1 - Modelagem de banco de dados** - Propor uma modelagem de banco de dados funcional e normalizada, adequada para armazenar os dados coletados pelos sensores.
* **2 - Modelo de Machine Learning** - Criar um modelo simples de Machine Learning, utilizando os dados gerados na entrega anterior (ou dados simulados).

## Premissas

### Foco no aprendizado
Em termos gerais, a principal diretriz foi conservar o caráter da prática das técnicas de modelagem de IA e de bases de dados, de forma a fixar o conhecimento e preparar-se para o exercício profissional, desenvolvendo o espírito investigativo e de melhoria contínua nas entregas.

### Uso de dados simulados
Apesar da nossa busca intensiva por datasets que representassem de forma adequada nosso problema, terminamos por criar um script para geração de um dataset simulado, que será descrito mais adiante.

### Visão conceitual da solução

![Visão conceitual da solução](assets/reply_3_overview.png)
*<center><sub>Visão geral simplificada da arquitetura</sub></center>*
Descrição
- As entregas desta fase, destacadas na figura acima, estão listadas no item **Entregáveis e localização**, no final deste documento.




# 1 - Modelagem de banco de dados

### Diagrama Entidade-Relacionamento



Descrição das tabelas e campos

Relacionamentos implícitos (loose coupling)

[figura DER]

SSoT - Single Source of Truth

[figura fluxo de dados]

Restrições de integridade (tipos de dados, limites de tamanho etc.);

Integração com visualização de dados



2 - Modelo de Machine Learning

Dados iniciais
Dados simulados
Os dados simulados foram criados a partir de um script Python. Algumas características desses dados:
Simulam o monitoramento de dois motores industriais idênticos.
Incluem dados por um período de 60 dias, com uma medição a cada 10 minutos.
Simulam uma falha progressiva em um dos equipamentos, a partir de 30 dias antes da falha total. O outro equipamento operará normalmente durante todo o período e servirá de linha de base.
O script para geração dos dados encontra-se em src/data_generation.ipynb.
Pré-processamento inicial
Os dados simulados não representam os dados crus coletados dos sensores. Em vez disso, eles recebem um primeiro tratamento, ou agregação em série temporal, já no computador de borda. Essa agregação sincroniza os dados dos sensores, combinados em um único pacote, em formato adequado para o envio.
Como a frequência de leitura dos sensores pode ser diferente, o computador de borda efetua uma média, de forma a obter um valor único por sensor a cada intervalo definido (no nosso caso, 10 minutos).
Os dados numéricos são formatados, para diminuir o volume enviado.
A ‘fonte da verdade’ - Dados puros versus registros de manutenção
Os dados que serão posteriormente utilizados para o treinamento dos modelos não são os dados puros recebidos do computador de borda e sim os registros enriquecidos de manutenção. Para compor esses registros e prepará-los para o treinamento de modelos, houve a intervenção de um engenheiro de dados que, a partir da ocorrência de uma falha, avaliou os dados históricos que levaram a ela, para identificar o início do comportamento anômalo causador da falha. Eis a sequência:
1 - Ocorre a falha
2 - Um técnico de manutenção registra o evento. Esse registro contém o dia e horário exatos da ocorrência e o motivo (ex.: desgaste do rolamento, bobina do estator em curto etc.).
3 - Com base nesses registros, o cientista de dados ou equivalente vai proceder à rotulagem dos dados que antecederam a falha (ou backwards labeling), para que eles contenham a informação adicional da quantidade de dias para a ocorrência da falha (days_to_failure) e o status (failure_mode). 
Esse processo deverá ser repetido para cada falha registrada. Isso permitirá que se construa um dataset completo e rotulado ao longo do tempo e que esses dados sejam a ‘fonte de verdade’ para o treinamento dos modelos.
Veja figura pipelines
Escolha da abordagem
Analisando detidamente o problema que estamos tentando resolver, ou seja, a predição de falhas em equipamentos industriais, percebemos que, embora sugira ser um simples problema de regressão, já que estamos analisando variáveis numéricas para determinar a quantidade de dias para falha (days-to-failure). Por outro lado, tratamos também de determinar o valor para uma categoria discreta (failure_mode), com o objetivo de determinar o estado do equipamento (normal ou anômalo)

Ao abraçar esses dois desafios, colocamo-nos diante de uma abordagem híbrida, com uma abordagem de classificação, para a emissão de alertas, e outra de regressão, para a construção de um prognóstico.

Exploração dos dados





### Diagrama Entidade-Relacionamento

![Diagrama Entidade-Relacionamento](assets/reply_3_DER.png)
*<center><sub>Diagrama Entidade-Relacionamento</sub></center>*

![Relacionamento implícito entre tabelas](assets/reply_3_loose_coupling.png)
*<center><sub>Relacionamento implícito entre tabelas</sub></center>*





---

### 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- <b>.github</b>: arquivos de configuração específicos do GitHub.

- <b>assets</b>: imagens.

- <b>documents</b>: documentos de projeto.

- <b>README.md</b>: este documento.

*Foram removidas as pastas default vazias.*

### 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>



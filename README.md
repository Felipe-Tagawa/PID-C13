# Parte Teórica

## 1. Funcionamento da planta

A planta é um **forno**, em que o objetivo é controlar a temperatura de acordo com um valor de referência definido pelo usuário. No projeto, essa referência é representada por **SP(s)**, enquanto a saída do processo é representada por **PV(s)**.

Por ser um sistema térmico, o forno não responde de forma instantânea. Quando o valor de referência muda, a temperatura leva um tempo para começar a variar e também leva um tempo até se aproximar de um novo valor de equilíbrio. Esse comportamento é compatível com sistemas de primeira ordem, como os sistemas térmicos citados no próprio material do trabalho.

Além disso, o sistema pode apresentar um atraso de transporte, também chamado de tempo morto. Esse atraso representa o tempo entre a aplicação de uma mudança na entrada e o início perceptível da resposta do sistema. Em processos térmicos isso pode acontecer por causa da própria inércia térmica do forno.

No ensaio utilizado para a identificação, é aplicada uma **mudança em degrau no sinal de referência** e a resposta da temperatura é observada ao longo do tempo. A partir dessa curva, são estimados os parâmetros do modelo da planta.

No dataset, a variável `in` representa o **SetPoint**, ou seja, a temperatura desejada para o sistema. A saída representa a temperatura medida do forno. O material também indica que o valor inicial do SetPoint na interface deve ser o mesmo presente no conjunto de dados utilizado.

Em uma aplicação real, a temperatura poderia ser medida por sensores como um **termopar** ou um **PT100**, que são bastante utilizados em sistemas térmicos. Já o aquecimento poderia ser feito por uma resistência elétrica, acionada por algum circuito de potência, como um relé de estado sólido, TRIAC ou outro dispositivo adequado.

De forma simplificada, o funcionamento seria:

**SetPoint → Controlador → Aquecedor → Forno → Sensor de temperatura**

---

## 2. Variáveis do sistema

A **variável controlada** é a temperatura do forno, já que essa é a grandeza que se deseja manter próxima do valor de referência. No sistema em malha fechada, essa temperatura medida é comparada com o SetPoint para gerar o erro utilizado pelo controlador.

O **SetPoint** é a temperatura de referência definida para o sistema. No dataset ele corresponde à variável `in`.

A **variável manipulada** é a ação aplicada ao sistema de aquecimento, ou seja, a potência fornecida à resistência elétrica. É por meio dessa potência que o controlador consegue aumentar ou diminuir a temperatura do forno.

As principais perturbações que podem afetar o sistema são:

- variação da temperatura ambiente;
- abertura da porta do forno;
- entrada ou retirada de materiais;
- variação da carga térmica;
- perdas de calor para o ambiente;
- variações na tensão de alimentação;
- ruídos na medição do sensor.

Essas perturbações podem fazer a temperatura se afastar do valor desejado, fazendo com que o controlador tenha que corrigir novamente a resposta.

Em relação às faixas de operação:

| Grandeza | Tipo | Faixa/condição de operação |
|---|---|---|
| Temperatura do forno | Variável controlada | mínimo e máximo observados no dataset |
| SetPoint | Referência | valores de `in` presentes no dataset |
| Potência do aquecedor | Variável manipulada | conforme o atuador utilizado |
| Temperatura ambiente | Perturbação | depende das condições do ambiente |
| Carga térmica | Perturbação | depende do material inserido no forno |

Assim, o sistema pode ser resumido da seguinte forma:

- **SetPoint:** temperatura desejada;
- **Variável controlada:** temperatura do forno;
- **Variável manipulada:** potência aplicada ao aquecedor;
- **Sensor:** termopar, PT100 ou similar;
- **Atuador:** resistência elétrica com circuito de acionamento;
- **Perturbações:** perdas térmicas, temperatura ambiente, abertura da porta, carga térmica e variações de alimentação.

# Parte Prática

## 3. Comparação e ajuste fino do modelo

Após a identificação da planta pelos métodos de Smith e Sundaresan, foi selecionado o método de **Sundaresan**, que apresentou melhor aproximação para os dados analisados.

O modelo considerado é:

$$
G(s)=\frac{K}{\tau s+1}e^{-\theta s}
$$

em que:

- **K** representa o ganho do processo;
- **τ** representa a constante de tempo;
- **θ** representa o tempo morto do sistema.

Para uma entrada degrau de amplitude $\Delta u$, a resposta temporal utilizada na etapa de ajuste é:

$$
y(t)=
\begin{cases}
0, & t<\theta \\
K\Delta u\left(1-e^{-\frac{t-\theta}{\tau}}\right), & t\geq\theta
\end{cases}
$$

### Avaliação da aproximação

A qualidade do modelo é avaliada comparando a resposta estimada com os dados experimentais.

O erro em cada instante é dado por:

$$
e_i=y_i-\hat{y}_i
$$

onde $y_i$ corresponde ao valor experimental e $\hat{y}_i$ ao valor estimado pelo modelo.

Como principal métrica de comparação é utilizado o **RMSE** (*Root Mean Squared Error*):

$$
RMSE=
\sqrt{
\frac{1}{n}
\sum_{i=1}^{n}
(y_i-\hat{y}_i)^2
}
$$

Também é calculado o erro absoluto máximo:

$$
E_{\max}=
\max |y_i-\hat{y}_i|
$$

Para facilitar a interpretação do resultado, o RMSE também é relacionado à amplitude total da resposta:

$$
A = y_{\max} - y_{\min}
$$

O RMSE relativo, em porcentagem, é calculado por:

$$
\frac{RMSE}{A} \times 100
$$

Na interface foi adotado o seguinte critério auxiliar:

- **até 5%:** aproximação satisfatória;
- **entre 5% e 10%:** aproximação razoável, podendo ser melhorada;
- **acima de 10%:** recomenda-se realizar o ajuste fino.

Esses valores são utilizados apenas como referência para auxiliar a análise da resposta.

### Comparação do modelo identificado

Para o método de **Sundaresan**, os parâmetros inicialmente identificados foram:

- $K = 0{,}6750$
- $\tau = 121{,}2030$ s
- $\theta = 23{,}7940$ s

Na etapa de comparação, o modelo apresentou:

- **RMSE:** 0,7548 °C
- **Erro máximo:** 2,4891 °C
- **RMSE em relação à amplitude:** 2,09%

Como o RMSE corresponde a apenas 2,09% da amplitude da resposta, a aproximação inicial já pode ser considerada satisfatória pelo critério adotado.

Mesmo assim, foi realizado um ajuste fino para verificar se seria possível melhorar a aproximação entre o modelo e os dados experimentais.

### Ajuste fino manual

A interface permite modificar individualmente os parâmetros $K$, $\tau$ e $\theta$ para observar o efeito de cada alteração sobre a resposta do sistema.

O efeito de cada parâmetro pode ser observado da seguinte forma:

- aumento de **K** → aumenta o valor final da resposta;
- redução de **K** → reduz o valor final da resposta;
- aumento de **τ** → torna a resposta mais lenta;
- redução de **τ** → torna a resposta mais rápida;
- aumento de **θ** → aumenta o atraso no início da resposta;
- redução de **θ** → faz a resposta começar mais cedo.

A cada alteração, a curva é recalculada e comparada novamente com os dados experimentais.

### Ajuste automático

Também foi implementado um ajuste automático utilizando a função `least_squares` da biblioteca SciPy.

O algoritmo procura novos valores de $K$, $\tau$ e $\theta$ que reduzam a diferença entre a resposta experimental e a resposta calculada pelo modelo.

Para cada amostra, o resíduo é calculado por:

$$
r_i=\hat{y}_i-y_i
$$

O método busca minimizar a soma dos quadrados desses resíduos:

$$
J(K,\tau,\theta)=
\sum_{i=1}^{n}
(\hat{y}_i-y_i)^2
$$

Após o ajuste automático, foram obtidos os seguintes parâmetros:

- $K = 0{,}66037$
- $\tau = 120{,}483$ s
- $\theta = 20{,}863$ s

O RMSE foi reduzido de:

$$
RMSE_{\text{identificado}} = 0{,}7548\ ^\circ C
$$

para:

$$
RMSE_{\text{ajustado}} = 0{,}5518\ ^\circ C
$$

A redução percentual foi de aproximadamente:

$$
\text{Redução}=
\frac{
0{,}7548-0{,}5518
}{
0{,}7548
}
\times100
\approx 26{,}90\%
$$

Após o ajuste, o RMSE passou a representar aproximadamente **1,53% da amplitude da resposta**, enquanto o nível de ruído estimado foi de **0,4299 °C**.

O ajuste modificou principalmente o ganho e o tempo morto do modelo. O ganho foi reduzido de 0,6750 para 0,66037, diminuindo levemente a amplitude final da resposta. A constante de tempo apresentou uma pequena redução, de 121,2030 s para 120,483 s, tornando a resposta ligeiramente mais rápida. Já o tempo morto foi reduzido de 23,7940 s para 20,863 s, fazendo com que a resposta estimada começasse mais cedo.

Assim, apesar de o modelo inicialmente identificado já apresentar uma aproximação satisfatória, o ajuste fino automático conseguiu melhorar a representação da resposta experimental, reduzindo o RMSE em aproximadamente **26,90%**.

## 7. Estrutura e funcionamento das abas desenvolvidas

A aplicação foi estruturada de forma modular em abas interativas, permitindo navegar desde a autenticação e inspeção dos dados experimentais até a modelagem matemática e simulação do controle em malha fechada.

### Aba Início
A aba Início é responsável pelo controle de autenticação e gerenciamento de acesso aos recursos da aplicação:
- Autenticação de usuários por meio de credenciais padrão (`admin`/`admin`).
- Persistência do estado da sessão (`st.session_state`), mantendo as variáveis e o fluxo entre as abas.
- Bloqueio das funcionalidades de identificação, dados e controle enquanto o usuário não realizar o login.
- Botão para encerramento da sessão (logout) e redefinição dos dados armazenados em memória.

### Aba Identificação
A aba Identificação realiza a modelagem paramétrica da planta térmica a partir dos dados do ensaio experimental:
- Leitura e carregamento de arquivos de ensaio nos formatos `.mat`, `.csv` e `.txt`.
- Pré-processamento dos sinais experimentais com remoção do offset térmico inicial pela média das primeiras amostras em repouso, referenciando o sistema ao ponto de operação.
- Identificação dos parâmetros da função de transferência de Primeira Ordem com Tempo Morto (FOPDT): ganho estático ($K$), constante de tempo ($\tau$) e tempo morto ($\theta$).
- Implementação de dois métodos clássicos de identificação baseados na curva de reação ao degrau: Smith e Sundaresan.
- Simulação do modelo estimado em malha aberta com aproximação de Padé de 1ª ordem para o atraso de transporte.
- Avaliação comparativa entre os modelos através do Erro Quadrático Médio (EQM/RMSE) em relação à curva experimental.
- Exibição da função de transferência $G(s)$, apresentação do gráfico comparativo da resposta temporal e armazenamento do modelo na sessão para utilização na aba de controle.

### Aba Dados
A aba Dados fornece uma visão direta da estrutura e da distribuição das grandezas contidas no arquivo de ensaio:
- Leitura de arquivos `.mat`, `.csv` ou `.txt` com extração dos vetores numéricos unidimensionais.
- Listagem de todas as variáveis e colunas encontradas no arquivo, informando o tipo de dado e quantidade de amostras.
- Cálculo de estatísticas descritivas para cada variável (valores mínimo, máximo e média).
- Identificação da variável correspondente à saída do processo (temperatura do forno / PV).
- Apresentação dos dados de saída em tabela indexada para visualização direta dos pontos experimentais.

### Aba Controle PID
A aba Controle PID executa o projeto e a simulação do sistema em malha fechada com realimentação unitária:
- Seleção entre dois modos de operação para a definição dos parâmetros do controlador:
  - Sintonia analítica: determinação automática dos ganhos a partir dos parâmetros FOPDT identificados, com suporte aos métodos de Ziegler-Nichols (curva de reação) e ITAE (seguimento de SetPoint), tanto para estruturas PI quanto PID.
  - Sintonia manual: ajuste interativo e direto dos parâmetros $K_p$, $T_i$ e $T_d$ pelo usuário.
- O parâmetro $\lambda$ (IMC) permanece fixo e bloqueado no valor 0.0, indicando a não utilização de métodos baseados em IMC no projeto.
- Simulação temporal da malha aberta e da malha fechada sob degrau de referência (SetPoint), considerando o atraso de transporte puro e filtro derivativo ($N=10$).
- Cálculo e exibição das métricas de desempenho transitório e permanente: tempo de subida ($t_r$), tempo de acomodação ($t_s$), sobressinal percentual ($\%OS$) e erro em regime permanente ($e_{ss}$).
- Tabela comparativa de desempenho entre os métodos e apresentação das equações matemáticas do controlador no domínio de Laplace e no domínio do tempo.



void FUN_0100_1722(void)

{
  char *pcVar1;
  char *pcVar2;
  int iVar3;
  char *pcVar4;
  char *unaff_DI;
  char *pcVar5;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
  iVar3 = 100;
  pcVar5 = unaff_DI;
  do {
    if (iVar3 == 0) break;
    iVar3 = iVar3 + -1;
    pcVar1 = pcVar5;
    pcVar5 = pcVar5 + 1;
  } while (*pcVar1 != '\0');
  pcVar5 = pcVar5 + -(int)unaff_DI;
  pcVar4 = pcVar5;
  FUN_0100_17f6();
  for (; pcVar4 != (char *)0x0; pcVar4 = pcVar4 + -1) {
    pcVar2 = pcVar5;
    pcVar5 = pcVar5 + 1;
    pcVar1 = unaff_DI;
    unaff_DI = unaff_DI + 1;
    *pcVar2 = *pcVar1;
  }
  return;
}


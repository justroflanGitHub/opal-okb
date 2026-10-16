
void FUN_0100_17a7(void)

{
  char *pcVar1;
  char *pcVar2;
  undefined2 uVar3;
  int iVar4;
  char *in_BX;
  char *pcVar5;
  char *pcVar6;
  char *pcVar7;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
  pcVar5 = (char *)0x0;
  do {
    if (*(int *)0x629 <= (int)pcVar5) {
      uRam00000143 = 0xffff;
      return;
    }
    pcVar6 = pcVar5;
    uVar3 = FUN_0100_17d6();
    iVar4 = 5;
    pcVar7 = in_BX;
    do {
      if (iVar4 == 0) break;
      iVar4 = iVar4 + -1;
      pcVar2 = pcVar7;
      pcVar7 = pcVar7 + 1;
      pcVar1 = pcVar6;
      pcVar6 = pcVar6 + 1;
    } while (*pcVar1 == *pcVar2);
    if (iVar4 == 0) {
      uRam00000143 = uVar3;
      return;
    }
    pcVar5 = pcVar5 + 1;
  } while( true );
}


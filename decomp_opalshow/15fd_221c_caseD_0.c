
/* WARNING: Control flow encountered bad instruction data */

void switchD_1000:6efd::caseD_0(void)

{
  int in_DX;
  int unaff_BP;
  int unaff_DI;
  undefined2 unaff_SS;
  
  *(int *)(unaff_BP + unaff_DI) = *(int *)(unaff_BP + unaff_DI) + in_DX;
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}

